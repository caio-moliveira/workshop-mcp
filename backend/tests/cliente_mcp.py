"""Auxiliares dos testes do servidor MCP: um cliente MCP falando o protocolo por HTTP.

O servidor é um endereço (o serviço `mcp` do compose) ou a aplicação criada pela fábrica, dentro
do processo. Nos dois casos o pedido passa pela camada HTTP, onde o token é conferido.

Este arquivo não pode se chamar `mcp.py`: esconderia o pacote `mcp` do SDK, que o FastMCP importa.
"""

import asyncio
import os
from collections.abc import Awaitable, Callable

import httpx2
from fastmcp import Client
from fastmcp.client.client import CallToolResult
from fastmcp.client.transports import StreamableHttpTransport
from mcp_types import Tool
from starlette.applications import Starlette

MCP_DO_AMBIENTE = f"http://127.0.0.1:{os.environ.get('MCP_PORT', '8001')}"
CAMINHO = "/mcp"
# A versão do protocolo MCP sem sessão, a que o cliente do FastMCP 4 negocia com o servidor.
PROTOCOLO_SEM_SESSAO = "2026-07-28"

# O erro único de ferramenta inexistente ou de outro perfil, e os demais erros genéricos (RS-08).
FERRAMENTA_DESCONHECIDA = "Ferramenta desconhecida."
PARAMETRO_INVALIDO = "Parâmetro inválido."
INDISPONIVEL = "Serviço indisponível."
ERRO_INTERNO = "Erro interno."


async def _com_cliente[R](
    servidor: str | Starlette, token: str, operacao: Callable[[Client], Awaitable[R]]
) -> R:
    if isinstance(servidor, str):
        async with Client(StreamableHttpTransport(servidor + CAMINHO, auth=token)) as cliente:
            return await operacao(cliente)

    def fabrica(**opcoes) -> httpx2.AsyncClient:
        return httpx2.AsyncClient(transport=httpx2.ASGITransport(app=servidor), **opcoes)

    transporte = StreamableHttpTransport(
        f"http://mcp.invalid{CAMINHO}", auth=token, httpx_client_factory=fabrica
    )
    async with servidor.router.lifespan_context(servidor), Client(transporte) as cliente:
        return await operacao(cliente)


def listar_ferramentas(servidor: str | Starlette, token: str) -> list[Tool]:
    """As ferramentas que o servidor lista para o token dado."""
    return asyncio.run(_com_cliente(servidor, token, lambda cliente: cliente.list_tools()))


def chamar(
    servidor: str | Starlette, token: str, ferramenta: str, argumentos: dict | None = None
) -> CallToolResult:
    """Chama a ferramenta e devolve o resultado, seja sucesso ou erro de ferramenta."""
    return asyncio.run(
        _com_cliente(
            servidor,
            token,
            lambda cliente: cliente.call_tool(ferramenta, argumentos, raise_on_error=False),
        )
    )


def pedir_ao_protocolo(
    http,
    token: str | None,
    metodo: str,
    parametros: dict | None = None,
    versao: str | None = None,
):
    """Um pedido JSON-RPC cru a `/mcp`, sem cliente MCP no meio, para ver a resposta HTTP inteira.

    `http` é qualquer cliente HTTP com `.post`: o `TestClient` da aplicação no processo (dentro de
    um `with`, que a inicia) ou um `httpx.Client` apontado para o servidor do ambiente.

    Sem `versao`, o pedido segue o protocolo anterior a 2026-07-28, que o servidor sem estado
    responde sem `initialize`. Com `PROTOCOLO_SEM_SESSAO`, segue o protocolo novo, o que o cliente
    do FastMCP negocia: a versão vai no cabeçalho e em `_meta`.
    """
    cabecalhos = {"Accept": "application/json, text/event-stream"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    corpo = {"jsonrpc": "2.0", "id": 1, "method": metodo}
    if parametros is not None:
        corpo["params"] = parametros
    if versao:
        cabecalhos |= {"MCP-Protocol-Version": versao, "Mcp-Method": metodo}
        if parametros and "name" in parametros:
            cabecalhos["Mcp-Name"] = parametros["name"]
        envelope = {
            "io.modelcontextprotocol/protocolVersion": versao,
            "io.modelcontextprotocol/clientCapabilities": {},
        }
        corpo["params"] = {**(parametros or {}), "_meta": envelope}
    return http.post(CAMINHO, json=corpo, headers=cabecalhos)


def chamar_pelo_protocolo(
    http, token: str, ferramenta: str, argumentos: dict | None = None, versao: str | None = None
):
    """A resposta HTTP crua de uma chamada de ferramenta, para comparar byte a byte."""
    return pedir_ao_protocolo(
        http, token, "tools/call", {"name": ferramenta, "arguments": argumentos or {}}, versao
    )


def assert_recusado(resposta) -> None:
    """A recusa do token: 401, sem dizer qual verificação falhou (RS-08)."""
    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"].startswith("Bearer")
    assert "mcp-session-id" not in resposta.headers


def texto_do_erro(resultado: CallToolResult) -> str:
    """A mensagem de um erro de ferramenta, que precisa ser a única coisa na resposta."""
    assert resultado.is_error
    assert resultado.structured_content is None
    assert len(resultado.content) == 1
    return resultado.content[0].text
