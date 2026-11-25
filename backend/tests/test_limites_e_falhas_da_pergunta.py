"""Os tetos da pergunta ao assistente e as falhas no meio da resposta.

Como na rota do assistente: a API é criada dentro do processo, com um modelo roteirizado, os
tetos montados pela fábrica, o token do provedor do compose e o serviço `mcp` do compose.
"""

import asyncio

import pytest
from pydantic_ai.models.function import FunctionModel
from recusa import RESPOSTA_DE_PARAMETRO_INVALIDO
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil
from assistente import Limites

UM_LACO = [("vendas_indicadores", {"periodo": "30d"})] * 20
# As mensagens genéricas do evento `erro`: não citam provedor, modelo nem ferramenta (RS-08).
TEMPO_ESGOTADO = "O assistente demorou demais para responder. Tente de novo."
SESSAO_EXPIRADA = "Sua sessão expirou. Entre de novo para continuar."


def _modelo_que_escreve_e_depois(acao) -> FunctionModel:
    """Escreve um trecho e então faz a `acao` (esperar, falhar) no meio da resposta."""

    async def responder(mensagens, info):
        yield "Os atrasos "
        await acao()
        yield "vêm da Transportadora X."

    return FunctionModel(stream_function=responder)


def _so_os_tipos(lidos) -> list[str]:
    return [tipo for tipo, _ in lidos]


def _fala(texto: str, autor: str = "usuario") -> dict:
    return {"autor": autor, "texto": texto}


@pytest.mark.parametrize(
    "corpo",
    [
        {"pergunta": "x" * 51},
        {"pergunta": "Oi?", "conversa": [_fala("Oi")] * 21},
        {"pergunta": "Oi?", "conversa": [_fala("Oi"), _fala("x" * 51, "assistente")]},
    ],
    ids=["pergunta-grande-demais", "conversa-com-itens-demais", "item-da-conversa-grande-demais"],
)
def test_pedido_acima_dos_tetos_recebe_400_antes_da_resposta(criar_api, token_de, corpo):
    api = criar_api(modelo=modelo_roteirizado(), limites=Limites(caracteres=50))

    resposta = perguntar(api, token_de(Perfil.VENDAS), corpo)

    assert resposta.status_code == 400
    assert resposta.json() == RESPOSTA_DE_PARAMETRO_INVALIDO


def test_modelo_lento_termina_com_erro_de_tempo_esgotado_sem_desfazer_o_texto(criar_api, token_de):
    async def demorar():
        await asyncio.sleep(5)

    api = criar_api(modelo=_modelo_que_escreve_e_depois(demorar), limites=Limites(segundos=0.5))

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS)))

    assert lidos == [("texto", {"texto": "Os atrasos "}), ("erro", {"erro": TEMPO_ESGOTADO})]


def test_pedido_no_limite_dos_tetos_e_aceito(criar_api, token_de):
    api = criar_api(modelo=modelo_roteirizado(), limites=Limites(caracteres=50))
    corpo = {"pergunta": "x" * 50, "conversa": [_fala("x" * 50)] * 20}

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS), corpo))

    assert lidos[-1][0] == "fim"


def test_o_modelo_em_laco_para_no_teto_de_chamadas_e_termina_com_fim_e_aviso(criar_api, token_de):
    api = criar_api(modelo=modelo_roteirizado(chamadas=UM_LACO), limites=Limites(chamadas=2))

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS)))

    tipo, dados = lidos[-1]
    assert tipo == "fim"
    assert dados["aviso"]
    assert [tipo for tipo, _ in lidos].count("estado") <= 3
    assert not any(tipo == "erro" for tipo, _ in lidos)
