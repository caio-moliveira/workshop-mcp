"""O tempo de cada rota de dados contra a meta de 3 segundos do RNF-05.

As rotas são lidas do registro (ver registros.py), e quem chama é o usuário do perfil dono de
cada uma. Uma rota nova entra na medição sem ninguém acrescentá-la a este teste.
"""

import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from provedor import USUARIOS_DE_DEMONSTRACAO
from recusa import pedir, pedir_eu
from registros import DONO_DA_ROTA

META_EM_SEGUNDOS = 3
# O maior período da enumeração: o que mais linhas lê.
PERIODO = "24m"


@pytest.fixture(scope="module")
def api_com_as_chaves(criar_api, token_de) -> Iterator[TestClient]:
    """Uma API só para o módulo, que já buscou as chaves do provedor.

    Assim cada rota é chamada uma vez só, e a medição não inclui a busca das chaves, que
    acontece uma vez na vida do serviço e não a cada consulta.
    """
    with criar_api() as api:
        assert pedir_eu(api, token_de(USUARIOS_DE_DEMONSTRACAO[0].perfil)).status_code == 200
        yield api


@pytest.mark.parametrize("rota", sorted(DONO_DA_ROTA))
def test_a_rota_responde_dentro_da_meta_em_24_meses(api_com_as_chaves, token_de, rota):
    token = token_de(DONO_DA_ROTA[rota])

    inicio = time.perf_counter()
    resposta = pedir(api_com_as_chaves, rota, token, periodo=PERIODO)
    duracao = time.perf_counter() - inicio

    assert resposta.status_code == 200
    assert duracao <= META_EM_SEGUNDOS, (
        f"{rota} levou {duracao:.2f} s em {PERIODO}; a meta é {META_EM_SEGUNDOS} s (RNF-05)"
    )
    print(f"{rota}: {duracao * 1000:.0f} ms")
