"""GET /comercial/funil: os leads criados no período em cada etapa do funil.

Os valores esperados vêm de consultas independentes, feitas com o papel dono nos dados de origem:
o período filtra pela data de criação e a etapa é a atual de cada lead (glossário). O banco é o da
carga padrão (data de referência 30/11/2026).
"""

from datetime import date

import pytest
from recusa import pedir

from acesso import Perfil

ROTA = "/comercial/funil"

# Os períodos que terminam em 30/11/2026, como em Vendas.
PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}
# A ordem do funil, com Perdido por último (glossário), repetida aqui de propósito.
ETAPAS = ["Novo", "Contatado", "Qualificado", "Proposta", "Fechado", "Perdido"]
# Os valores dos dados atuais (spec #87), contados à parte nos dados de origem.
LEADS_CONHECIDOS = {"30d": [49, 0, 0, 0, 4, 14], "12m": [76, 38, 40, 27, 110, 455]}


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.COMERCIAL)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


def _na_origem(conexao, datas) -> dict[str, int]:
    """Os leads criados no período em cada etapa."""
    return dict(
        conexao.execute(
            "select etapa, count(*) from dados_de_origem.lead"
            " where data_criacao between %s and %s group by etapa",
            datas,
        ).fetchall()
    )


@pytest.mark.parametrize("periodo", PERIODOS)
def test_as_seis_etapas_vem_na_ordem_do_funil_com_perdido_por_ultimo(respostas, periodo):
    resposta = respostas[periodo]

    assert resposta.status_code == 200
    assert [item["etapa"] for item in resposta.json()["etapas"]] == ETAPAS


@pytest.mark.parametrize("periodo", LEADS_CONHECIDOS)
def test_as_contagens_sao_as_conhecidas_dos_dados_atuais(respostas, periodo):
    """Em 30 dias as etapas do meio não têm lead e vêm com zero."""
    contagens = [item["leads"] for item in respostas[periodo].json()["etapas"]]

    assert contagens == LEADS_CONHECIDOS[periodo]


@pytest.mark.parametrize("periodo", PERIODOS)
def test_as_contagens_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    na_origem = _na_origem(conexao_dono, PERIODOS[periodo])

    assert respostas[periodo].json()["etapas"] == [
        {"etapa": etapa, "leads": na_origem.get(etapa, 0)} for etapa in ETAPAS
    ]


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    inicio, fim = PERIODOS[periodo]

    assert respostas[periodo].json()["periodo"] == {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
    }


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.COMERCIAL))

    assert resposta.json() == respostas["12m"].json()


def test_resposta_tem_so_o_periodo_e_as_etapas(respostas):
    assert set(respostas["12m"].json()) == {"periodo", "etapas"}
