"""A conversa com o assistente: perguntas de continuação e a pergunta abandonada pelo navegador.

A conversa anterior vem no corpo, montada pelo navegador, e chega ao modelo como contexto. A API
é criada dentro do processo, com um modelo roteirizado no lugar do modelo de linguagem.
"""

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil


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
