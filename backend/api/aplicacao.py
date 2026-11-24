"""Fábrica da aplicação FastAPI."""

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.datastructures import QueryParams

from acesso import (
    ConfiguracaoDeAcesso,
    ProvedorIndisponivel,
    TokenRecusado,
    UsuarioAutenticado,
    autenticar,
)
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

# A mesma resposta para toda recusa: quem chama não sabe qual verificação falhou (RS-08).
RECUSA = {"erro": "Não autenticado."}
# A mesma negação em toda rota de dados: não diz se os dados existem (RF-11).
NEGACAO = {"erro": "Acesso negado."}
# Não descreve a validação, não ecoa o valor nem nomes internos (RS-08).
PARAMETRO_INVALIDO = {"erro": "Parâmetro inválido."}
# O provedor ou o banco fora do ar não é culpa do token: o cliente não deve mandar o usuário ao
# login.
INDISPONIVEL = {"erro": "Serviço indisponível."}

# As rotas que só exigem um usuário autenticado, sem perfil. Toda outra rota serve uma consulta,
# e o perfil é o que a consulta declara (RS-05).
ROTAS_SO_AUTENTICADAS = frozenset({"/eu"})

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
    """O único parâmetro previsto é `periodo`, uma vez só. Nada de filtro livre."""
    if set(parametros.keys()) - {"periodo"} or len(parametros.getlist("periodo")) > 1:
        raise ParametroInvalido("parâmetro fora do previsto")
    return Periodo.ler(parametros.get("periodo", PERIODO_PADRAO))


def criar_aplicacao(
    configuracao: ConfiguracaoDeAcesso, origem_do_frontend: str, consultas: ExecutorDeConsultas
) -> FastAPI:
    """A API valida tokens pela configuração dada, lê o banco só pelo executor de consultas e só
    aceita o navegador vindo do frontend."""
    # Sem /docs, /redoc nem /openapi.json: a API não descreve as próprias rotas a ninguém.
    aplicacao = FastAPI(title="pulso.", docs_url=None, redoc_url=None, openapi_url=None)
    # O token vai no cabeçalho Authorization, nunca em cookie: não há credenciais de navegador.
    aplicacao.add_middleware(
        CORSMiddleware,
        allow_origins=[origem_do_frontend],
        allow_methods=["GET"],
        allow_headers=["Authorization"],
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

    def usuario_autenticado(request: Request) -> UsuarioAutenticado:
        esquema, _, token = request.headers.get("authorization", "").partition(" ")
        if esquema.lower() != "bearer" or not token:
            raise TokenRecusado("cabeçalho Authorization ausente ou sem Bearer")
        return autenticar(token, configuracao)

    @aplicacao.get("/eu")
    def eu(usuario: Annotated[UsuarioAutenticado, Depends(usuario_autenticado)]) -> dict:
        return {"nome": usuario.nome, "perfil": usuario.perfil}

    def servir(consulta: Consulta) -> Callable:
        # Ordem fixa: token (na dependência), perfil, parâmetros e só então a consulta.
        def endpoint(
            request: Request,
            usuario: Annotated[UsuarioAutenticado, Depends(usuario_autenticado)],
        ):
            consultas.autorizar(usuario, consulta)
            periodo = ler_periodo(request.query_params)
            return consultas.executar(usuario, consulta, periodo=periodo)

        return endpoint

    for caminho, consulta in ROTAS_DE_DADOS.items():
        aplicacao.router.routes.append(RotaDeConsulta(caminho, servir(consulta), consulta))

    return aplicacao
