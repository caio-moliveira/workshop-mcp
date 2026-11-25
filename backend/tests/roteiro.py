"""Auxiliares dos testes do assistente: um modelo roteirizado e a leitura do fluxo de eventos.

O modelo roteirizado faz o papel do modelo de linguagem: o roteiro decide quais ferramentas ele
chama e que texto ele devolve. Todo o resto é de verdade: a API, o token do provedor e o serviço
`mcp` do compose.
"""

import json
from collections.abc import Sequence
from typing import Any

from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel

ROTA = "/assistente"


def modelo_roteirizado(
    chamadas: Sequence[tuple[str, dict[str, Any]]] = (),
    pedacos: Sequence[str] = ("Resposta ", "do assistente."),
    vistos: dict[str, Any] | None = None,
) -> FunctionModel:
    """Chama as ferramentas do roteiro, uma por vez e em ordem, e então escreve os pedaços.

    Em `vistos`, se dado, fica o que o modelo recebeu na última requisição: as mensagens e os
    nomes das ferramentas oferecidas.
    """

    async def responder(mensagens: list[ModelMessage], info: AgentInfo):
        if vistos is not None:
            vistos["mensagens"] = mensagens
            vistos["ferramentas"] = [ferramenta.name for ferramenta in info.function_tools]
        feitas = sum(
            isinstance(parte, ToolCallPart)
            for mensagem in mensagens
            if isinstance(mensagem, ModelResponse)
            for parte in mensagem.parts
        )
        if feitas < len(chamadas):
            nome, argumentos = chamadas[feitas]
            yield {
                0: DeltaToolCall(
                    name=nome, json_args=json.dumps(argumentos), tool_call_id=f"chamada-{feitas}"
                )
            }
            return
        for pedaco in pedacos:
            yield pedaco

    return FunctionModel(stream_function=responder)


def perguntar(api, token: str | None, corpo: dict[str, Any] | None = None, **cabecalhos: str):
    """POST na rota do assistente, com o token no cabeçalho Authorization."""
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    return api.post(ROTA, json=corpo or {"pergunta": "O que está causando os atrasos?"}, headers=cabecalhos)


def eventos(resposta) -> list[tuple[str, Any]]:
    """Os eventos do fluxo, em ordem, como (tipo, dados)."""
    assert resposta.status_code == 200, resposta.text
    assert resposta.headers["content-type"].startswith("text/event-stream")
    lidos = []
    for bloco in resposta.text.split("\n\n"):
        campos = dict(
            linha.split(": ", 1) for linha in bloco.splitlines() if not linha.startswith(":")
        )
        if campos:
            lidos.append((campos["event"], json.loads(campos["data"])))
    return lidos
