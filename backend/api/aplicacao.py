"""Fábrica da aplicação FastAPI."""

import logging
import uuid
from collections.abc import AsyncIterator, Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal

import anyio
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, PlainSerializer, StringConstraints
from pydantic_ai.models import Model
from starlette.datastructures import QueryParams

from acesso import (
    ConfiguracaoDeAcesso,
    ProvedorIndisponivel,
    TokenRecusado,
    UsuarioAutenticado,
    autenticar,
    mensagens,
)
from assistente import Assistente, ItemDaConversa, Limites
from assistente.limites import ITENS_DA_CONVERSA
from assistente.limites import PADRAO as LIMITES_PADRAO
from assistente.resposta import ConversaDaPergunta, RespostaEmCurso
from consultas import (
    PERIODO_PADRAO,
    AcessoNegado,
    Consulta,
    ConsultaFalhou,
    ExecutorDeConsultas,
    ParametroInvalido,
    Periodo,
    vendas,
)
from historico import (
    ChamadaRastreada,
    ConversaGravada,
    ConversaInexistente,
    Historico,
    HistoricoIndisponivel,
    ItemGravado,
    RespostaParaGravar,
    Situacao,
)

registro = logging.getLogger("api")

# As respostas de erro, uma por situação, com os textos comuns ao servidor MCP: a mesma recusa
# para todo token recusado e a mesma negação em toda rota de dados (RS-08, RF-11).
RECUSA = {"erro": mensagens.NAO_AUTENTICADO}
NEGACAO = {"erro": mensagens.ACESSO_NEGADO}
PARAMETRO_INVALIDO = {"erro": mensagens.PARAMETRO_INVALIDO}
INDISPONIVEL = {"erro": mensagens.SERVICO_INDISPONIVEL}
ERRO_INTERNO = {"erro": mensagens.ERRO_INTERNO}
ASSISTENTE_INDISPONIVEL = {"erro": mensagens.ASSISTENTE_INDISPONIVEL}
CONVERSA_INEXISTENTE = {"erro": mensagens.CONVERSA_INEXISTENTE}

# As rotas que só exigem um usuário autenticado, sem perfil. Toda outra rota serve uma consulta,
# e o perfil é o que a consulta declara (RS-05). O assistente não tem regra de perfil própria: o
# que ele alcança é o que o servidor MCP lista e permite para o token do usuário (RF-13).
# O histórico também não: cada usuário só alcança as próprias conversas, com o perfil que tinha
# ao criá-las (RF-18).
ROTAS_SO_AUTENTICADAS = frozenset(
    {"/eu", "/assistente", "/conversas", "/conversas/{id_da_conversa}"}
)


class Pergunta(BaseModel):
    """O corpo da rota do assistente. Campos fora do previsto são recusados, entre eles a conversa
    reenviada da 5a: o que vai ao modelo é a conversa gravada, nunca a do navegador (ADR 0009)."""

    model_config = ConfigDict(extra="forbid")

    pergunta: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    # Sem ele, a pergunta abre uma conversa nova. Texto, e não UUID: fora do formato, é uma
    # conversa que não existe (404), como no caminho das rotas do histórico.
    id_da_conversa: str | None = None


@dataclass(frozen=True)
class PerguntaGravada:
    """A pergunta aceita e já gravada, com a conversa como estava antes dela."""

    texto: str
    id_da_conversa: uuid.UUID
    id_da_pergunta: uuid.UUID
    anteriores: tuple[ItemGravado, ...]


class AssistenteIndisponivel(Exception):
    """Não há modelo de linguagem configurado, ou falta a chave do provedor."""


# Cada rota de dados e a consulta que ela serve. Todas recebem só o período.
ROTAS_DE_DADOS: dict[str, Consulta] = {
    "/vendas/indicadores": vendas.indicadores,
    "/vendas/evolucao": vendas.evolucao,
    "/vendas/situacao-das-entregas": vendas.situacao_das_entregas,
    "/vendas/pedidos-recentes": vendas.pedidos_recentes,
}


class RotaDeConsulta(APIRoute):
    """Uma rota GET que serve uma consulta. O perfil da rota é o perfil da consulta."""

    def __init__(self, caminho: str, endpoint: Callable, consulta: Consulta) -> None:
        self.consulta = consulta
        super().__init__(caminho, endpoint, methods=["GET"], name=consulta.nome)


def ler_periodo(parametros: QueryParams) -> Periodo:
    """O único parâmetro previsto é `periodo`, uma vez só. Nada além dele."""
    if set(parametros.keys()) - {"periodo"} or len(parametros.getlist("periodo")) > 1:
        raise ParametroInvalido("parâmetro fora do previsto")
    return Periodo.ler(parametros.get("periodo", PERIODO_PADRAO))


def conversa_para_o_modelo(itens: Iterable[ItemGravado]) -> list[ItemDaConversa]:
    """A conversa gravada como o modelo a recebe: os pares de pergunta e resposta, na ordem das
    perguntas.

    Cada resposta vai com a pergunta que ela responde, pelo identificador da pergunta: duas
    perguntas feitas ao mesmo tempo ficam gravadas antes das duas respostas, e cada resposta acha
    a sua. A pergunta gravada antes de o identificador ser gravado com ela não o tem: a resposta
    logo depois dela é a dela.

    Uma resposta sem texto (parada antes de escrever, ou com erro logo no início) fica de fora com
    a pergunta dela: o modelo não recebe pergunta sem resposta.
    """
    gravados = list(itens)
    perguntas: dict[uuid.UUID, tuple[int, ItemGravado]] = {}
    pares: list[tuple[int, ItemGravado, ItemGravado]] = []
    for posicao, item in enumerate(gravados):
        if item.autor == "usuario":
            if item.id_da_pergunta:
                perguntas[item.id_da_pergunta] = (posicao, item)
            continue
        achada = perguntas.get(item.id_da_pergunta) if item.id_da_pergunta else None
        anterior = gravados[posicao - 1] if posicao else None
        if (
            achada is None
            and anterior
            and anterior.autor == "usuario"
            and anterior.id_da_pergunta is None
        ):
            achada = (posicao - 1, anterior)
        if achada and item.texto:
            pares.append((achada[0], achada[1], item))
    pares.sort(key=lambda par: par[0])
    conversa = [
        ItemDaConversa(autor=item.autor, texto=item.texto)
        for _, pergunta, resposta in pares
        for item in (pergunta, resposta)
    ]
    # O teto conta os itens que o modelo recebe, não os gravados: primeiro saem os pares sem
    # texto, e só então ficam os mais recentes, até o teto. Um número par de itens: nenhum par
    # fica pela metade.
    cabem = ITENS_DA_CONVERSA - ITENS_DA_CONVERSA % 2
    return conversa[-cabem:]


def identificador_da_conversa(valor: str) -> uuid.UUID:
    """O identificador da conversa, no caminho ou no corpo. Fora do formato, é uma conversa que
    não existe: o mesmo 404, sem dizer que o formato estava errado."""
    try:
        return uuid.UUID(valor)
    except ValueError as erro:
        raise ConversaInexistente() from erro


# A data como `isoformat()`, com o fuso em `+00:00`, e não em `Z` como o Pydantic a escreveria.
Horario = Annotated[datetime, PlainSerializer(datetime.isoformat, return_type=str)]


class ConversaNaLista(BaseModel):
    """Uma conversa na lista: sem os itens."""

    id: uuid.UUID
    titulo: str
    ultima_atividade: Horario


class ListaDeConversas(BaseModel):
    conversas: list[ConversaNaLista]


class ItemLido(BaseModel):
    """Um item da conversa lida. Só a resposta tem situação, aviso, erro, pergunta e rastreio: o
    campo que o item não tem fica fora do JSON (a rota exclui os vazios)."""

    autor: Literal["usuario", "assistente"]
    texto: str
    situacao: Situacao | None = None
    aviso: str | None = None
    erro: str | None = None
    id_da_pergunta: uuid.UUID | None = None
    # Na resposta, sempre presente, mesmo vazio: sem chamadas, a tela diz que nenhuma ferramenta
    # foi consultada.
    rastreio: list[ChamadaRastreada] | None = None

    @classmethod
    def do_historico(cls, item: ItemGravado) -> "ItemLido":
        if (fim := item.fim) is None:
            return cls(autor=item.autor, texto=item.texto)
        return cls(
            autor=item.autor,
            texto=item.texto,
            situacao=fim.situacao,
            aviso=fim.aviso,
            erro=fim.erro,
            id_da_pergunta=item.id_da_pergunta,
            rastreio=list(fim.rastreio),
        )


class ConversaLida(BaseModel):
    id: uuid.UUID
    titulo: str
    itens: list[ItemLido]

    @classmethod
    def do_historico(cls, conversa: ConversaGravada) -> "ConversaLida":
        itens = [ItemLido.do_historico(item) for item in conversa.itens]
        return cls(id=conversa.id, titulo=conversa.titulo, itens=itens)


def criar_aplicacao(
    configuracao: ConfiguracaoDeAcesso,
    origem_do_frontend: str,
    consultas: ExecutorDeConsultas,
    modelo: Model | None,
    endereco_do_mcp: str,
    historico: Historico,
    limites: Limites = LIMITES_PADRAO,
) -> FastAPI:
    """A API valida tokens pela configuração dada, lê o banco só pelo executor de consultas e só
    aceita o navegador vindo do frontend.

    O assistente responde com o modelo dado (sem ele, fica indisponível) e com as ferramentas do
    servidor MCP do endereço dado, chamado com o token de quem pergunta. Cada pergunta e cada
    resposta ficam gravadas no histórico dado, que é também de onde vem a conversa entregue ao
    modelo.
    """
    assistente = Assistente(modelo, endereco_do_mcp, limites)
    # Sem /docs, /redoc nem /openapi.json: a API não descreve as próprias rotas a ninguém.
    aplicacao = FastAPI(title="pulso.", docs_url=None, redoc_url=None, openapi_url=None)
    # O token vai no cabeçalho Authorization, nunca em cookie: não há credenciais de navegador.
    aplicacao.add_middleware(
        CORSMiddleware,
        allow_origins=[origem_do_frontend],
        # DELETE só para apagar uma conversa do histórico.
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @aplicacao.exception_handler(TokenRecusado)
    def recusar(_: Request, erro: TokenRecusado) -> JSONResponse:
        registro.warning("token recusado: %s", erro)
        return JSONResponse(RECUSA, status_code=401, headers={"WWW-Authenticate": "Bearer"})

    @aplicacao.exception_handler(ProvedorIndisponivel)
    def provedor_indisponivel(_: Request, erro: ProvedorIndisponivel) -> JSONResponse:
        registro.error("provedor de identidade indisponível: %s", erro)
        return JSONResponse(INDISPONIVEL, status_code=503)

    @aplicacao.exception_handler(AcessoNegado)
    def negar(_: Request, erro: AcessoNegado) -> JSONResponse:
        registro.warning("acesso negado: %s", erro)
        return JSONResponse(NEGACAO, status_code=403)

    @aplicacao.exception_handler(ParametroInvalido)
    @aplicacao.exception_handler(RequestValidationError)
    def parametro_invalido(_: Request, erro: Exception) -> JSONResponse:
        registro.info("parâmetro inválido: %s", erro)
        return JSONResponse(PARAMETRO_INVALIDO, status_code=400)

    @aplicacao.exception_handler(ConsultaFalhou)
    def banco_indisponivel(_: Request, erro: ConsultaFalhou) -> JSONResponse:
        registro.error("consulta falhou: %s", erro)
        return JSONResponse(INDISPONIVEL, status_code=503)

    @aplicacao.exception_handler(ConversaInexistente)
    def conversa_inexistente(_: Request, erro: ConversaInexistente) -> JSONResponse:
        registro.info("conversa inexistente ou de outro usuário")
        return JSONResponse(CONVERSA_INEXISTENTE, status_code=404)

    @aplicacao.exception_handler(HistoricoIndisponivel)
    def historico_indisponivel(_: Request, erro: HistoricoIndisponivel) -> JSONResponse:
        registro.error("histórico indisponível: %s", erro)
        return JSONResponse(INDISPONIVEL, status_code=503)

    @aplicacao.exception_handler(AssistenteIndisponivel)
    def sem_assistente(_: Request, erro: AssistenteIndisponivel) -> JSONResponse:
        registro.warning("assistente indisponível: %s", erro)
        return JSONResponse(ASSISTENTE_INDISPONIVEL, status_code=503)

    @aplicacao.exception_handler(Exception)
    def erro_inesperado(_: Request, erro: Exception) -> JSONResponse:
        registro.error("erro inesperado: %s", erro, exc_info=erro)
        return JSONResponse(ERRO_INTERNO, status_code=500)

    def token_do_pedido(request: Request) -> str:
        esquema, _, token = request.headers.get("authorization", "").partition(" ")
        if esquema.lower() != "bearer" or not token:
            raise TokenRecusado("cabeçalho Authorization ausente ou sem Bearer")
        return token

    # O token cru da requisição, para o assistente repassar ao servidor MCP.
    Token = Annotated[str, Depends(token_do_pedido)]

    def usuario_autenticado(token: Token) -> UsuarioAutenticado:
        return autenticar(token, configuracao)

    # O usuário do token da requisição; sem token válido, a recusa (401) vem antes de tudo.
    Autenticado = Annotated[UsuarioAutenticado, Depends(usuario_autenticado)]

    def assistente_disponivel() -> Assistente:
        if not assistente.disponivel:
            raise AssistenteIndisponivel("sem modelo de linguagem configurado ou sem a chave")
        return assistente

    def pergunta_dentro_dos_tetos(corpo: Pergunta) -> Pergunta:
        # O teto de caracteres vem da configuração: o modelo do corpo não o conhece.
        if len(corpo.pergunta) > limites.caracteres:
            raise ParametroInvalido("pergunta acima do teto de caracteres")
        return corpo

    def pergunta_gravada(
        usuario: Autenticado,
        _: Annotated[Assistente, Depends(assistente_disponivel)],
        corpo: Annotated[Pergunta, Depends(pergunta_dentro_dos_tetos)],
    ) -> PerguntaGravada:
        # A pergunta fica gravada antes de o modelo ser chamado: sem o histórico, ela não é
        # respondida, para a resposta não se perder. A conversa inexistente (404) vem antes.
        # Gravada com o identificador dela, que a resposta leva também: é o que as liga.
        id_da_pergunta = uuid.uuid4()
        try:
            if corpo.id_da_conversa is None:
                id_da_conversa = historico.criar_conversa(usuario, corpo.pergunta, id_da_pergunta)
                anteriores: tuple[ItemGravado, ...] = ()
            else:
                id_da_conversa = identificador_da_conversa(corpo.id_da_conversa)
                anteriores = historico.ler_conversa(usuario, id_da_conversa).itens
                historico.gravar_pergunta(usuario, id_da_conversa, corpo.pergunta, id_da_pergunta)
        except HistoricoIndisponivel as erro:
            # Só o tipo da falha: o detalhe do banco pode citar a linha recusada, com o texto da
            # pergunta, que nunca vai para o log.
            falha = type(erro.__cause__ or erro).__name__
            raise AssistenteIndisponivel(
                f"histórico indisponível ao gravar a pergunta ({falha})"
            ) from erro
        return PerguntaGravada(corpo.pergunta, id_da_conversa, id_da_pergunta, anteriores)

    def gravar_resposta(
        usuario: UsuarioAutenticado, pergunta: PerguntaGravada, resposta: RespostaParaGravar
    ) -> None:
        # Quem leu a resposta já a tem na tela: uma falha aqui fica só no log.
        try:
            historico.gravar_resposta(usuario, pergunta.id_da_conversa, resposta)
        except (HistoricoIndisponivel, ConversaInexistente) as erro:
            registro.error(
                "resposta não gravada: conversa %s, pergunta %s, usuário %s: %r",
                pergunta.id_da_conversa,
                pergunta.id_da_pergunta,
                usuario.id,
                erro,
            )

    @aplicacao.get("/eu")
    def eu(usuario: Autenticado) -> dict:
        return {"nome": usuario.nome, "perfil": usuario.perfil}

    # Validações antes do fluxo, como erro JSON: token (401), assistente (503), corpo (400),
    # conversa (404) e a gravação da pergunta (503). Só depois a resposta 200 começa, em eventos,
    # e o primeiro diz a conversa e a pergunta.
    @aplicacao.post("/assistente", response_class=EventSourceResponse)
    async def perguntar(
        usuario: Autenticado,
        token: Token,
        disponivel: Annotated[Assistente, Depends(assistente_disponivel)],
        pergunta: Annotated[PerguntaGravada, Depends(pergunta_gravada)],
    ) -> AsyncIterator[ServerSentEvent]:
        inicio = ConversaDaPergunta(pergunta.id_da_conversa, pergunta.id_da_pergunta)
        yield ServerSentEvent(event=inicio.tipo, data=inicio.dados)
        em_curso = RespostaEmCurso()
        try:
            async for evento in disponivel.responder(
                pergunta.texto,
                usuario,
                token,
                conversa_para_o_modelo(pergunta.anteriores),
                id_da_pergunta=pergunta.id_da_pergunta,
                id_da_conversa=pergunta.id_da_conversa,
            ):
                em_curso.acompanhar(evento)
                yield ServerSentEvent(event=evento.tipo, data=evento.dados)
        finally:
            # Vale também quando o navegador desconecta: o cancelamento não alcança a gravação,
            # e a resposta parada fica gravada com o texto que já tinha saído.
            resposta = em_curso.para_gravar(pergunta.id_da_pergunta)
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(gravar_resposta, usuario, pergunta, resposta)

    @aplicacao.get("/conversas")
    def listar_conversas(usuario: Autenticado) -> ListaDeConversas:
        resumos = historico.listar_conversas(usuario)
        return ListaDeConversas(
            conversas=[
                ConversaNaLista(id=r.id, titulo=r.titulo, ultima_atividade=r.ultima_atividade)
                for r in resumos
            ]
        )

    @aplicacao.get("/conversas/{id_da_conversa}", response_model_exclude_none=True)
    def ler_conversa(id_da_conversa: str, usuario: Autenticado) -> ConversaLida:
        identificador = identificador_da_conversa(id_da_conversa)
        return ConversaLida.do_historico(historico.ler_conversa(usuario, identificador))

    # Definitivo, e só no histórico: a auditoria das chamadas da conversa fica (ADR 0009).
    @aplicacao.delete("/conversas/{id_da_conversa}", status_code=204)
    def apagar_conversa(id_da_conversa: str, usuario: Autenticado) -> Response:
        historico.apagar_conversa(usuario, identificador_da_conversa(id_da_conversa))
        return Response(status_code=204)

    def servir(consulta: Consulta) -> Callable:
        # Ordem fixa: token (na dependência), perfil, parâmetros e só então a consulta.
        def endpoint(request: Request, usuario: Autenticado) -> dict:
            consultas.autorizar(usuario, consulta)
            periodo = ler_periodo(request.query_params)
            return consultas.executar(usuario, consulta, periodo=periodo)

        return endpoint

    for caminho, consulta in ROTAS_DE_DADOS.items():
        aplicacao.router.routes.append(RotaDeConsulta(caminho, servir(consulta), consulta))

    return aplicacao
