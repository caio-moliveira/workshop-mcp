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

from acesso import mensagens

ROTA = "/assistente"
# A mensagem genérica, igual na resposta 503 e no evento de erro: não cita provedor, modelo nem
# ferramenta (RS-08).
ASSISTENTE_INDISPONIVEL = mensagens.ASSISTENTE_INDISPONIVEL
RESPOSTA_DO_ASSISTENTE_INDISPONIVEL = {"erro": ASSISTENTE_INDISPONIVEL}


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
    if corpo is None:
        corpo = {"pergunta": "O que está causando os atrasos?"}
    return api.post(ROTA, json=corpo, headers=cabecalhos)


def conversa_gravada(criar_api, token: str, itens: Sequence[dict[str, str]]) -> str | None:
    """Grava pela rota, no histórico, uma conversa com os pares de pergunta e resposta dados, e
    devolve o identificador dela. Cada resposta sai de um modelo roteirizado que a escreve.

    Sem itens, nada é gravado: a pergunta seguinte abre uma conversa nova.
    """
    id_da_conversa = None
    for pergunta, resposta in zip(itens[::2], itens[1::2], strict=True):
        api = criar_api(modelo=modelo_roteirizado(pedacos=[resposta["texto"]]))
        corpo = {"pergunta": pergunta["texto"]}
        if id_da_conversa:
            corpo["id_da_conversa"] = id_da_conversa
        tipo, dados = eventos(perguntar(api, token, corpo))[0]
        assert tipo == "conversa"
        id_da_conversa = dados["id_da_conversa"]
    return id_da_conversa


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
