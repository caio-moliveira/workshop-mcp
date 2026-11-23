"""Fábrica da aplicação FastAPI."""

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from acesso import ConfiguracaoDeAcesso, TokenRecusado, UsuarioAutenticado, autenticar

registro = logging.getLogger("api")

# A mesma resposta para toda recusa: quem chama não sabe qual verificação falhou (RS-08).
RECUSA = {"erro": "Não autenticado."}


def criar_aplicacao(configuracao: ConfiguracaoDeAcesso) -> FastAPI:
    aplicacao = FastAPI(title="pulso.")

    @aplicacao.exception_handler(TokenRecusado)
    def recusar(_: Request, erro: TokenRecusado) -> JSONResponse:
        registro.warning("token recusado: %s", erro)
        return JSONResponse(RECUSA, status_code=401, headers={"WWW-Authenticate": "Bearer"})

    def usuario_autenticado(request: Request) -> UsuarioAutenticado:
        esquema, _, token = request.headers.get("authorization", "").partition(" ")
        if esquema.lower() != "bearer" or not token:
            raise TokenRecusado("cabeçalho Authorization ausente ou sem Bearer")
        return autenticar(token, configuracao)

    @aplicacao.get("/eu")
    def eu(usuario: Annotated[UsuarioAutenticado, Depends(usuario_autenticado)]) -> dict:
        return {"nome": usuario.nome, "perfil": usuario.perfil}

    return aplicacao
