"""GET /produtos/notas: quantas avaliações o período teve em cada nota, de 1 a 5.

Os valores esperados vêm de consultas independentes, feitas com o papel dono nos dados de origem:
o período filtra pela data da avaliação (glossário). O banco é o da carga padrão (data de
referência 30/11/2026). A ferramenta `produtos_notas` devolve o mesmo conteúdo; ela é chamada no
servidor MCP criado dentro do processo.
"""

from datetime import date

import pytest
from cliente_mcp import chamar
from recusa import pedir

from acesso import Perfil

ROTA = "/produtos/notas"
FERRAMENTA = "produtos_notas"

# Os períodos que terminam em 30/11/2026, como em Vendas.
PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.PRODUTOS)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


def _na_origem(conexao, datas) -> dict[int, int]:
    linhas = conexao.execute(
        """
        select nota, count(*) from dados_de_origem.avaliacao
        where data_avaliacao between %s and %s group by nota
        """,
        datas,
    ).fetchall()
    return dict(linhas)


@pytest.mark.parametrize("periodo", PERIODOS)
def test_as_cinco_notas_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    resposta = respostas[periodo]
    na_origem = _na_origem(conexao_dono, PERIODOS[periodo])

    assert resposta.status_code == 200
    assert resposta.json()["notas"] == [
        {"nota": nota, "avaliacoes": na_origem.get(nota, 0)} for nota in range(1, 6)
    ]


def test_nos_24_meses_as_contagens_sao_as_conhecidas(respostas):
    """Os números da spec #77, contados à parte."""
    contagens = [item["avaliacoes"] for item in respostas["24m"].json()["notas"]]

    assert contagens == [1382, 1169, 1988, 5329, 10246]


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    inicio, fim = PERIODOS[periodo]

    assert respostas[periodo].json()["periodo"] == {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
    }


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.PRODUTOS))

    assert resposta.json() == respostas["12m"].json()


def test_resposta_tem_so_o_periodo_e_as_notas(respostas):
    assert set(respostas["12m"].json()) == {"periodo", "notas"}


@pytest.fixture(scope="module")
def mcp(criar_mcp):
    return criar_mcp()


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_conteudo_da_rota(mcp, respostas, token_de, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    resultado = chamar(mcp, token_de(Perfil.PRODUTOS), FERRAMENTA, {"periodo": periodo})

    assert not resultado.is_error
    assert resultado.structured_content == respostas[periodo].json()
