"""A conversa com o assistente: perguntas de continuação e a pergunta abandonada pelo navegador.

A conversa anterior vem no corpo, montada pelo navegador, e chega ao modelo como contexto. A API
é criada dentro do processo, com um modelo roteirizado no lugar do modelo de linguagem.
"""

import asyncio
import json
import threading
import time

from apoio import ultima_chamada_de
from provedor import conteudo
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
from roteiro import ROTA, eventos, modelo_roteirizado, perguntar

from acesso import Perfil

PERGUNTA = {"pergunta": "O que está causando os atrasos?"}
# Quanto o modelo roteirizado demora antes da segunda chamada, se não for cancelado.
ESPERA_DO_MODELO = 2


def _falas(mensagens) -> list[tuple[str, str]]:
    """As falas que o modelo recebeu, em ordem, como (autor, texto)."""
    falas = []
    for mensagem in mensagens:
        for parte in mensagem.parts:
            if isinstance(mensagem, ModelRequest) and isinstance(parte, UserPromptPart):
                falas.append(("usuario", parte.content))
            elif isinstance(mensagem, ModelResponse) and isinstance(parte, TextPart):
                falas.append(("assistente", parte.content))
    return falas


def test_a_conversa_enviada_chega_ao_modelo_na_ordem_antes_da_pergunta(criar_api, token_de):
    vistos: dict = {}
    api = criar_api(modelo=modelo_roteirizado(vistos=vistos))
    corpo = {
        "pergunta": "e por lojista?",
        "conversa": [
            {"autor": "usuario", "texto": "O que está causando os atrasos?"},
            {"autor": "assistente", "texto": "A **Transportadora X** concentra os atrasos."},
            {"autor": "usuario", "texto": "Desde quando?"},
            {"autor": "assistente", "texto": "Desde março."},
        ],
    }

    eventos(perguntar(api, token_de(Perfil.VENDAS), corpo))

    assert _falas(vistos["mensagens"]) == [
        ("usuario", "O que está causando os atrasos?"),
        ("assistente", "A **Transportadora X** concentra os atrasos."),
        ("usuario", "Desde quando?"),
        ("assistente", "Desde março."),
        ("usuario", "e por lojista?"),
    ]


def test_quando_o_cliente_desconecta_a_execucao_e_cancelada_sem_novas_chamadas(
    criar_api, token_de
):
    token = token_de(Perfil.VENDAS)
    usuario = conteudo(token)["sub"]
    na_segunda_requisicao = threading.Event()
    cancelada = threading.Event()
    feitas = 0

    async def responder(mensagens: list[ModelMessage], info: AgentInfo):
        # Chama uma ferramenta; na requisição seguinte demora e então chamaria outra.
        nonlocal feitas
        feitas += 1
        if feitas > 1:
            na_segunda_requisicao.set()
            try:
                await asyncio.sleep(ESPERA_DO_MODELO)
            except asyncio.CancelledError:
                cancelada.set()
                raise
        yield {
            0: DeltaToolCall(
                name="vendas_indicadores",
                json_args=json.dumps({"periodo": "30d"}),
                tool_call_id=f"chamada-{feitas}",
            )
        }

    api = criar_api(modelo=FunctionModel(stream_function=responder))

    with api.stream("POST", ROTA, json=PERGUNTA, headers={"Authorization": f"Bearer {token}"}):
        # A primeira chamada já terminou quando o modelo recebe a segunda requisição.
        assert na_segunda_requisicao.wait(timeout=30)
        depois_da_primeira = ultima_chamada_de(usuario)

    assert cancelada.wait(timeout=5)
    time.sleep(ESPERA_DO_MODELO + 1)
    assert depois_da_primeira is not None
    assert ultima_chamada_de(usuario) == depois_da_primeira
    assert feitas == 2
