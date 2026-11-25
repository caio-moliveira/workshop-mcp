"""O modelo de linguagem do assistente vem da configuração, sem mudança de código (RF-16).

O provedor lê a chave direto das variáveis de ambiente do processo; os testes as trocam com o
`monkeypatch`, sem chave de verdade.
"""

import pytest

from assistente import MODELO_PADRAO, modelo_do_ambiente


@pytest.fixture
def com_chave(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-de-teste")


def test_sem_a_variavel_o_assistente_usa_o_modelo_padrao(monkeypatch, com_chave):
    monkeypatch.delenv("MODELO_DO_ASSISTENTE", raising=False)

    modelo = modelo_do_ambiente()

    assert MODELO_PADRAO == "anthropic:claude-haiku-5-5"
    assert modelo is not None
    assert modelo.system == "anthropic"
    assert modelo.model_name == "claude-haiku-5-5"


def test_a_variavel_vazia_tambem_usa_o_modelo_padrao(monkeypatch, com_chave):
    monkeypatch.setenv("MODELO_DO_ASSISTENTE", "")

    modelo = modelo_do_ambiente()

    assert modelo is not None
    assert modelo.model_name == "claude-haiku-5-5"


def test_outro_valor_da_variavel_da_outro_modelo(monkeypatch, com_chave):
    monkeypatch.setenv("MODELO_DO_ASSISTENTE", "anthropic:claude-sonnet-5")

    modelo = modelo_do_ambiente()

    assert modelo is not None
    assert modelo.model_name == "claude-sonnet-5"


def test_modelo_de_outro_provedor_tambem_vem_da_variavel(monkeypatch):
    monkeypatch.setenv("MODELO_DO_ASSISTENTE", "test")

    modelo = modelo_do_ambiente()

    assert modelo is not None
    assert modelo.system == "test"


@pytest.mark.parametrize("chave", [None, ""], ids=["ausente", "vazia"])
def test_sem_a_chave_do_provedor_o_assistente_fica_indisponivel(monkeypatch, chave):
    monkeypatch.delenv("MODELO_DO_ASSISTENTE", raising=False)
    if chave is None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ANTHROPIC_API_KEY", chave)

    assert modelo_do_ambiente() is None


def test_modelo_desconhecido_deixa_o_assistente_indisponivel(monkeypatch, com_chave):
    monkeypatch.setenv("MODELO_DO_ASSISTENTE", "naoexiste:x")

    assert modelo_do_ambiente() is None
