"""Fábrica do servidor MCP: as consultas de negócio como ferramentas, com o isolamento por perfil.

O servidor não tem regra própria de token nem de perfil: o token é conferido pelo `acesso` e o
perfil pelo executor de consultas, os mesmos que a API usa (RF-13).
"""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import anyio
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, RemoteAuthProvider, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import Tool, ToolResult
from mcp.server.auth.handlers.metadata import ProtectedResourceMetadataHandler
from mcp.server.auth.routes import build_resource_metadata_url
from mcp.shared.auth import ProtectedResourceMetadata
from pydantic import AnyHttpUrl, PrivateAttr
from starlette.applications import Starlette
from starlette.middleware import Middleware as MiddlewareHTTP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from acesso import (
    ConfiguracaoDeAcesso,
    ProvedorIndisponivel,
    TokenRecusado,
    UsuarioAutenticado,
    autenticar,
    mensagens,
)
from auditoria import Auditoria, AuditoriaIndisponivel, Chamada, Resultado
from consultas import AcessoNegado, ConsultaFalhou, ExecutorDeConsultas, ParametroInvalido
from servidor_mcp.ferramentas import FERRAMENTAS, Ferramenta
from servidor_mcp.limite import LimiteDeFrequencia

registro = logging.getLogger("servidor_mcp")

CAMINHO = "/mcp"
# Responde sem token: é o que o healthcheck do compose pede.
CAMINHO_DA_SAUDE = "/saude"


class ErroDaChamada(ToolError):
    """Um erro de ferramenta com mensagem genérica e o desfecho que vai para a auditoria.

    Quem o levanta já pôs o motivo no log: por isso o FastMCP não o loga de novo.
    """

    def __init__(self, mensagem: str, resultado: Resultado) -> None:
        super().__init__(mensagem, log_level=logging.DEBUG)
        self.resultado = resultado


class TokenDoUsuario(AccessToken):
    """O token aceito, com o usuário que o `acesso` autenticou."""

    usuario: UsuarioAutenticado


class VerificadorDeToken(TokenVerifier):
    """Entrega cada token ao `autenticar` do `acesso`. Nenhuma regra de validação mora aqui."""

    def __init__(self, configuracao: ConfiguracaoDeAcesso) -> None:
        super().__init__()
        self._configuracao = configuracao

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            # A busca das chaves do provedor bloqueia: fora do laço de eventos.
            usuario = await anyio.to_thread.run_sync(autenticar, token, self._configuracao)
        except TokenRecusado as erro:
            registro.warning("token recusado: %s", erro)
            return None
        # O `acesso` não diz qual aplicação pediu o token; o FastMCP só exige um identificador.
        return TokenDoUsuario(
            token=token, client_id=usuario.id, scopes=[], subject=usuario.id, usuario=usuario
        )


class RecursoProtegido(RemoteAuthProvider):
    """A autenticação do servidor como recurso protegido do OAuth (RFC 9728).

    Publica os metadados de recurso protegido, com o endereço público do servidor como recurso e
    o realm do provedor como servidor de autorização, e a recusa (401) passa a apontá-los no
    `WWW-Authenticate`. Quem confere o token continua sendo o `VerificadorDeToken`.
    """

    def __init__(self, configuracao: ConfiguracaoDeAcesso, endereco_publico: str) -> None:
        super().__init__(
            token_verifier=VerificadorDeToken(configuracao),
            # O emissor dos tokens é o próprio realm.
            authorization_servers=[AnyHttpUrl(configuracao.emissor)],
            base_url=endereco_publico,
            # Os escopos que o cliente pede no login. `pulso-mcp` põe no token o destinatário e o
            # perfil para os clientes registrados dinamicamente (ADR 0007); a validação do token
            # não olha escopo nenhum.
            scopes_supported=["openid", "pulso-mcp"],
        )

    def get_routes(self, mcp_path: str | None = None) -> list[Route]:
        """A rota dos metadados, sem o CORS aberto a toda origem que o SDK põe nela.

        Nenhum navegador precisa lê-los: o MCP Inspector busca os metadados e fala com o servidor
        pelo backend dele, e os assistentes externos, pelos servidores deles.
        """
        self.set_mcp_path(mcp_path)
        recurso = self._get_resource_url(mcp_path)
        metadados = ProtectedResourceMetadata(
            resource=recurso,
            authorization_servers=self.authorization_servers,
            scopes_supported=self.scopes_supported,
        )
        caminho = urlsplit(str(build_resource_metadata_url(recurso))).path
        return [
            Route(
                caminho,
                endpoint=ProtectedResourceMetadataHandler(metadados).handle,
                methods=["GET"],
            )
        ]

    def get_middleware(self) -> list:
        return [MiddlewareHTTP(_ProvedorIndisponivel), *super().get_middleware()]


class _ProvedorIndisponivel:
    """Sem as chaves do provedor não há como conferir o token: 503, e não 401 nem 500."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await self._app(scope, receive, send)
        except ProvedorIndisponivel as erro:
            registro.error("provedor de identidade indisponível: %s", erro)
            resposta = JSONResponse({"erro": mensagens.SERVICO_INDISPONIVEL}, status_code=503)
            await resposta(scope, receive, send)


def _usuario_do_token() -> UsuarioAutenticado | None:
    """O usuário do token da requisição. O perfil vem só daqui (RS-03)."""
    token = get_access_token()
    return token.usuario if isinstance(token, TokenDoUsuario) else None


def _pode_usar(
    usuario: UsuarioAutenticado | None, ferramenta: Ferramenta, consultas: ExecutorDeConsultas
) -> bool:
    """Se o perfil do usuário é o da consulta da ferramenta. Quem decide é o executor."""
    if usuario is None:
        return False
    try:
        consultas.autorizar(usuario, ferramenta.consulta)
    except AcessoNegado:
        return False
    return True


class FerramentaDeConsulta(Tool):
    """Uma ferramenta do registro, publicada no servidor: valida os argumentos e roda a consulta."""

    _ferramenta: Ferramenta = PrivateAttr()
    _consultas: ExecutorDeConsultas = PrivateAttr()

    def __init__(self, nome: str, ferramenta: Ferramenta, consultas: ExecutorDeConsultas) -> None:
        super().__init__(
            name=nome,
            title=ferramenta.titulo,
            description=ferramenta.descricao,
            parameters=ferramenta.esquema_de_entrada(),
            annotations={"readOnlyHint": True, "openWorldHint": False},
        )
        self._ferramenta = ferramenta
        self._consultas = consultas

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        """Ordem fixa: token (já conferido na chegada), perfil, parâmetros e só então a consulta."""
        usuario = _usuario_do_token()
        consulta = self._ferramenta.consulta
        try:
            if usuario is None:
                raise AcessoNegado(f"chamada sem usuário autenticado a {self.name}")
            self._consultas.autorizar(usuario, consulta)
            parametros = self._ferramenta.ler_argumentos(arguments)
            # A consulta bloqueia numa conexão do pool: fora do laço de eventos.
            resultado = await anyio.to_thread.run_sync(
                lambda: self._consultas.executar(usuario, consulta, **parametros)
            )
        except AcessoNegado as erro:
            registro.warning("acesso negado: %s", erro)
            raise ErroDaChamada(mensagens.FERRAMENTA_DESCONHECIDA, Resultado.NEGADA) from erro
        except ParametroInvalido as erro:
            registro.info("parâmetro inválido em %s: %s", self.name, erro)
            raise ErroDaChamada(
                mensagens.PARAMETRO_INVALIDO, Resultado.PARAMETRO_INVALIDO
            ) from erro
        except ConsultaFalhou as erro:
            registro.error("consulta falhou: %s", erro)
            raise ErroDaChamada(mensagens.SERVICO_INDISPONIVEL, Resultado.FALHA) from erro
        except Exception as erro:
            registro.error("erro inesperado em %s: %s", self.name, erro, exc_info=erro)
            raise ErroDaChamada(mensagens.ERRO_INTERNO, Resultado.FALHA) from erro
        return ToolResult(structured_content=resultado)


class FerramentasDoPerfil(Middleware):
    """Só as ferramentas do perfil do token aparecem na listagem e respondem à chamada.

    A chamada a um nome que não está no registro recebe aqui o mesmo erro da ferramenta de outro
    perfil, antes que o FastMCP responda com o nome pedido na mensagem.
    """

    def __init__(self, consultas: ExecutorDeConsultas) -> None:
        self._consultas = consultas

    def _visivel(self, nome: str) -> bool:
        ferramenta = FERRAMENTAS.get(nome)
        return ferramenta is not None and _pode_usar(
            _usuario_do_token(), ferramenta, self._consultas
        )

    async def on_list_tools(self, context: MiddlewareContext, call_next) -> Sequence[Tool]:
        return [
            ferramenta for ferramenta in await call_next(context) if self._visivel(ferramenta.name)
        ]

    async def on_call_tool(self, context: MiddlewareContext, call_next) -> ToolResult:
        if not self._visivel(context.message.name):
            usuario = _usuario_do_token()
            registro.warning(
                "perfil %s pediu uma ferramenta de outro perfil ou inexistente: %r",
                usuario.perfil if usuario else None,
                context.message.name,
            )
            raise ErroDaChamada(mensagens.FERRAMENTA_DESCONHECIDA, Resultado.NEGADA)
        return await call_next(context)


class ChamadaLimitada(ErroDaChamada):
    """A chamada barrada pelo limite de frequência: um erro de ferramenta, não um HTTP 429.

    Como erro de ferramenta, o assistente explica ao usuário o que houve, em vez de tratar como
    queda do servidor.
    """

    def __init__(self) -> None:
        super().__init__(mensagens.MUITAS_CHAMADAS, Resultado.LIMITADA)


class LimiteDasChamadas(Middleware):
    """Barra quem passou do limite de frequência, antes do filtro de ferramentas do perfil.

    Vem antes do filtro para que as chamadas negadas e com parâmetro inválido também contem: quem
    sonda o servidor é contido. Listar ferramentas não passa por aqui.
    """

    def __init__(self, limite: LimiteDeFrequencia) -> None:
        self._limite = limite

    async def on_call_tool(self, context: MiddlewareContext, call_next) -> ToolResult:
        usuario = _usuario_do_token()
        if usuario is not None and not self._limite.admitir(usuario.id):
            registro.warning("usuário %s passou do limite de frequência", usuario.id)
            raise ChamadaLimitada()
        return await call_next(context)


class AuditoriaDasChamadas(Middleware):
    """Grava cada chamada na auditoria, com o desfecho, antes de a resposta sair (RF-30).

    Fica por fora de todas as outras etapas, para enxergar o desfecho de cada uma. O horário é o
    da chegada da chamada.
    """

    def __init__(self, auditoria: Auditoria) -> None:
        self._auditoria = auditoria

    async def on_call_tool(self, context: MiddlewareContext, call_next) -> ToolResult:
        chegada = datetime.now(UTC)
        try:
            resposta = await call_next(context)
        except ErroDaChamada as erro:
            await self._registrar(context, erro.resultado, chegada)
            raise
        except Exception:
            # O que escapou das etapas já foi para o log de quem o levantou.
            await self._registrar(context, Resultado.FALHA, chegada)
            raise
        await self._registrar(context, Resultado.PERMITIDA, chegada)
        return resposta

    async def _registrar(
        self, context: MiddlewareContext, resultado: Resultado, chegada: datetime
    ) -> None:
        usuario = _usuario_do_token()
        if usuario is None:
            # O token é conferido na chegada: sem usuário, algo saiu do lugar. Sem ele não há
            # registro, e nenhuma chamada é respondida sem registro (ADR 0008).
            registro.error(
                "chamada %s a %r sem usuário autenticado: recusada sem registro",
                resultado,
                context.message.name,
            )
            raise ErroDaChamada(mensagens.ERRO_INTERNO, Resultado.FALHA)
        chamada = Chamada(
            usuario=usuario,
            ferramenta=context.message.name,
            argumentos=context.message.arguments or {},
            resultado=resultado,
            horario=chegada,
        )
        try:
            # A gravação bloqueia numa conexão do pool: fora do laço de eventos.
            await anyio.to_thread.run_sync(self._auditoria.registrar, chamada)
        except AuditoriaIndisponivel as erro:
            # Nenhuma chamada é respondida sem registro, nem a que deu certo (ADR 0008).
            registro.error("auditoria indisponível, chamada %s recusada: %s", resultado, erro)
            raise ErroDaChamada(mensagens.SERVICO_INDISPONIVEL, Resultado.FALHA) from erro


def criar_servidor(
    configuracao: ConfiguracaoDeAcesso,
    consultas: ExecutorDeConsultas,
    auditoria: Auditoria,
    endereco_publico: str,
    limite: LimiteDeFrequencia,
) -> FastMCP:
    """O servidor MCP com as ferramentas do registro. Só ferramentas: sem recursos nem prompts.

    Toda chamada fica na `auditoria`, e cada usuário cabe no `limite` de frequência. O
    `endereco_publico` é onde quem está fora do ambiente alcança o servidor (sem o `/mcp`): é o
    recurso anunciado nos metadados de recurso protegido.
    """
    servidor = FastMCP(
        "pulso.",
        instructions=(
            "Consultas somente leitura aos dados do marketplace pulso. As ferramentas "
            "disponíveis dependem do perfil do usuário autenticado."
        ),
        auth=RecursoProtegido(configuracao, endereco_publico),
        # O primeiro da lista é o mais externo.
        middleware=[
            AuditoriaDasChamadas(auditoria),
            LimiteDasChamadas(limite),
            FerramentasDoPerfil(consultas),
        ],
        # Rede de segurança: uma exceção que escape não leva o próprio texto a quem chamou.
        mask_error_details=True,
    )
    for nome, ferramenta in FERRAMENTAS.items():
        servidor.add_tool(FerramentaDeConsulta(nome, ferramenta, consultas))

    @servidor.custom_route(CAMINHO_DA_SAUDE, methods=["GET"])
    async def saude(_: Request) -> Response:
        return JSONResponse({"situacao": "no ar"})

    return servidor


def criar_aplicacao(
    configuracao: ConfiguracaoDeAcesso,
    consultas: ExecutorDeConsultas,
    auditoria: Auditoria,
    endereco_publico: str,
    limite: LimiteDeFrequencia,
) -> Starlette:
    """A aplicação HTTP do servidor MCP: streamable HTTP sem estado, em `/mcp` (RF-26).

    Valida tokens pela configuração dada, lê o banco só pelo executor de consultas, grava cada
    chamada na auditoria e barra quem passa do limite. Publica os metadados de recurso protegido em
    `/.well-known/oauth-protected-resource/mcp`.
    """
    return criar_servidor(configuracao, consultas, auditoria, endereco_publico, limite).http_app(
        path=CAMINHO, stateless_http=True, json_response=True
    )
