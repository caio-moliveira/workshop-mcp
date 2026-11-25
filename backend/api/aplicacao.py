"""Fábrica da aplicação FastAPI."""

import logging
from collections.abc import AsyncIterator, Callable
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
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
from assistente import Assistente
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

registro = logging.getLogger("api")

# As respostas de erro, uma por situação, com os textos comuns ao servidor MCP: a mesma recusa
# para todo token recusado e a mesma negação em toda rota de dados (RS-08, RF-11).
RECUSA = {"erro": mensagens.NAO_AUTENTICADO}
NEGACAO = {"erro": mensagens.ACESSO_NEGADO}
PARAMETRO_INVALIDO = {"erro": mensagens.PARAMETRO_INVALIDO}
INDISPONIVEL = {"erro": mensagens.SERVICO_INDISPONIVEL}
ERRO_INTERNO = {"erro": mensagens.ERRO_INTERNO}
ASSISTENTE_INDISPONIVEL = {"erro": mensagens.ASSISTENTE_INDISPONIVEL}

# As rotas que só exigem um usuário autenticado, sem perfil. Toda outra rota serve uma consulta,
# e o perfil é o que a consulta declara (RS-05). O assistente não tem regra de perfil própria: o
# que ele alcança é o que o servidor MCP lista e permite para o token do usuário (RF-13).
ROTAS_SO_AUTENTICADAS = frozenset({"/eu", "/assistente"})


class ItemDaConversa(BaseModel):
    """Uma fala anterior da conversa, como o navegador a guardou."""

    model_config = ConfigDict(extra="forbid")

    autor: Literal["usuario", "assistente"]
    texto: str


class Pergunta(BaseModel):
    """O corpo da rota do assistente. Campos fora do previsto são recusados."""

    model_config = ConfigDict(extra="forbid")

    pergunta: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    conversa: list[ItemDaConversa] = Field(default_factory=list)


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


def criar_aplicacao(
    configuracao: ConfiguracaoDeAcesso,
    origem_do_frontend: str,
    consultas: ExecutorDeConsultas,
    modelo: Model | None,
    endereco_do_mcp: str,
) -> FastAPI:
    """A API valida tokens pela configuração dada, lê o banco só pelo executor de consultas e só
    aceita o navegador vindo do frontend.

    O assistente responde com o modelo dado (sem ele, fica indisponível) e com as ferramentas do
    servidor MCP do endereço dado, chamado com o token de quem pergunta.
    """
    assistente = Assistente(modelo, endereco_do_mcp)
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

    @aplicacao.get("/eu")
    def eu(usuario: Autenticado) -> dict:
        return {"nome": usuario.nome, "perfil": usuario.perfil}

    # Validações antes do fluxo, como erro JSON: token (401), assistente (503), corpo (400). Só
    # depois a resposta 200 começa, em eventos.
    @aplicacao.post("/assistente", response_class=EventSourceResponse)
    async def perguntar(
        usuario: Autenticado,
        token: Token,
        disponivel: Annotated[Assistente, Depends(assistente_disponivel)],
        corpo: Pergunta,
    ) -> AsyncIterator[ServerSentEvent]:
        conversa = [(item.autor, item.texto) for item in corpo.conversa]
        async for evento in disponivel.responder(corpo.pergunta, usuario, token, conversa):
            yield ServerSentEvent(event=evento.tipo, data=evento.dados)

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
