"""A rota do assistente: a pergunta respondida em fluxo de eventos (RF-12, RF-14, RF-15).

A API é criada dentro do processo, com um modelo roteirizado no lugar do modelo de linguagem. O
token vem do provedor do compose e as ferramentas, do serviço `mcp` do compose, pela rede.
"""

import pytest
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil


@pytest.fixture
def com_roteiro(criar_api):
    def criar(**roteiro):
        return criar_api(modelo=modelo_roteirizado(**roteiro))

    return criar


def test_a_resposta_chega_em_varios_trechos_e_termina_com_fim(com_roteiro, token_de):
    api = com_roteiro(pedacos=["Os atrasos ", "vêm da ", "**Transportadora X**."])

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS)))

    trechos = [dados["texto"] for tipo, dados in lidos if tipo == "texto"]
    assert len(trechos) > 1
    assert "".join(trechos) == "Os atrasos vêm da **Transportadora X**."
    assert lidos[-1][0] == "fim"
    assert [tipo for tipo, _ in lidos].count("fim") == 1
