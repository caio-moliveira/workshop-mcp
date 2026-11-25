"""Fábrica da aplicação FastAPI."""

import logging
import uuid
from collections.abc import AsyncIterator, Callable, Iterable
from dataclasses import dataclass
from typing import Annotated

import anyio
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, StringConstraints
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
from assistente import Assistente, Evento, ItemDaConversa, Limites
from assistente.limites import ITENS_DA_CONVERSA
from assistente.limites import PADRAO as LIMITES_PADRAO
from assistente.resposta import conversa as evento_da_conversa
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
ROTAS_SO_AUTENTICADAS = frozenset({"/eu", "/assistente", "/conversas/{id_da_conversa}"})


class Pergunta(BaseModel):
    """O corpo da rota do assistente. Campos fora do previsto são recusados, entre eles a conversa
    reenviada da 5a: o que vai ao modelo é a conversa gravada, nunca a do navegador (ADR 0009)."""

    model_config = ConfigDict(extra="forbid")

    pergunta: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    # Sem ele, a pergunta abre uma conversa nova.
    id_da_conversa: uuid.UUID | None = None


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
    """A conversa gravada como o modelo a recebe: só os pares de pergunta e resposta em que a
    resposta tem texto, e só os mais recentes que cabem no teto de itens.

    Uma resposta sem texto (parada antes de escrever, ou com erro logo no início) fica de fora com
    a pergunta dela: o modelo não recebe pergunta sem resposta.
    """
    gravados = list(itens)
    pares: list[ItemDaConversa] = []
    for anterior, item in zip(gravados, gravados[1:], strict=False):
        if anterior.autor == "usuario" and item.autor == "assistente" and item.texto:
            pares += [
                ItemDaConversa(autor="usuario", texto=anterior.texto),
                ItemDaConversa(autor="assistente", texto=item.texto),
            ]
    # Um número par de itens: nenhum par fica pela metade.
    cabem = ITENS_DA_CONVERSA - ITENS_DA_CONVERSA % 2
    return pares[-cabem:]


def resposta_para_gravar(
    id_da_pergunta: uuid.UUID, trechos: Iterable[str], desfecho: Evento | None
) -> RespostaParaGravar:
    """A resposta como vai para o histórico. Sem `fim` nem `erro`, ela foi interrompida."""
    texto = "".join(trechos)
    if desfecho is None:
        return RespostaParaGravar(id_da_pergunta, texto, Situacao.INTERROMPIDA)
    if desfecho.tipo == "erro":
        return RespostaParaGravar(id_da_pergunta, texto, Situacao.ERRO, erro=desfecho.dados["erro"])
    return RespostaParaGravar(
        id_da_pergunta, texto, Situacao.CONCLUIDA, aviso=desfecho.dados.get("aviso")
    )


def conversa_como_resposta(conversa: ConversaGravada) -> dict:
    """A conversa lida, como a rota a devolve: só os campos que o item tem."""
    itens = []
    for item in conversa.itens:
        lido: dict = {"autor": item.autor, "texto": item.texto}
        if item.situacao:
            lido["situacao"] = item.situacao.value
        if item.aviso:
            lido["aviso"] = item.aviso
        if item.erro:
            lido["erro"] = item.erro
        if item.id_da_pergunta:
            lido["id_da_pergunta"] = str(item.id_da_pergunta)
        itens.append(lido)
    return {"id": str(conversa.id), "titulo": conversa.titulo, "itens": itens}


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
        allow_methods=["GET", "POST"],
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
        try:
            if corpo.id_da_conversa is None:
                id_da_conversa = historico.criar_conversa(usuario, corpo.pergunta)
                anteriores: tuple[ItemGravado, ...] = ()
            else:
                id_da_conversa = corpo.id_da_conversa
                anteriores = historico.ler_conversa(usuario, id_da_conversa).itens
            historico.gravar_pergunta(usuario, id_da_conversa, corpo.pergunta)
        except HistoricoIndisponivel as erro:
            raise AssistenteIndisponivel(f"histórico indisponível: {erro}") from erro
        return PerguntaGravada(corpo.pergunta, id_da_conversa, uuid.uuid4(), anteriores)

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
        inicio = evento_da_conversa(pergunta.id_da_conversa, pergunta.id_da_pergunta)
        yield ServerSentEvent(event=inicio.tipo, data=inicio.dados)
        trechos: list[str] = []
        desfecho: Evento | None = None
        try:
            async for evento in disponivel.responder(
                pergunta.texto, usuario, token, conversa_para_o_modelo(pergunta.anteriores)
            ):
                if evento.tipo == "texto":
                    trechos.append(evento.dados["texto"])
                elif evento.tipo in ("fim", "erro"):
                    desfecho = evento
                yield ServerSentEvent(event=evento.tipo, data=evento.dados)
        finally:
            # Vale também quando o navegador desconecta: o cancelamento não alcança a gravação,
            # e a resposta parada fica gravada com o texto que já tinha saído.
            resposta = resposta_para_gravar(pergunta.id_da_pergunta, trechos, desfecho)
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(gravar_resposta, usuario, pergunta, resposta)

    @aplicacao.get("/conversas/{id_da_conversa}")
    def ler_conversa(id_da_conversa: str, usuario: Autenticado) -> dict:
        # Um identificador fora do formato também é uma conversa que não existe.
        try:
            identificador = uuid.UUID(id_da_conversa)
        except ValueError as erro:
            raise ConversaInexistente() from erro
        return conversa_como_resposta(historico.ler_conversa(usuario, identificador))

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
