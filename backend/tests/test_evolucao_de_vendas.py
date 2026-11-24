"""GET /vendas/evolucao: pedidos e receita do período agrupados por dia, semana ou mês (RF-10).

Os valores esperados vêm dos dados de origem, lidos com o papel dono, e são agrupados aqui em
Python, independentemente do SQL da consulta: o dia de cada pedido no horário de Brasília, a semana
começando na segunda e o mês no dia 1. O banco é o da carga padrão (data de referência 30/11/2026).
"""

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

import pytest
from recusa import pedir

from acesso import Perfil

ROTA = "/vendas/evolucao"

# O período efetivo, contado à mão, e o agrupamento de cada um.
PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30), "dia"),
    "90d": (date(2026, 9, 2), date(2026, 11, 30), "semana"),
    "12m": (date(2025, 12, 1), date(2026, 11, 30), "mes"),
    "24m": (date(2024, 12, 1), date(2026, 11, 30), "mes"),
}

_PEDIDOS_NA_ORIGEM = """
select (p.momento_compra at time zone 'America/Sao_Paulo')::date, g.situacao, g.valor
from dados_de_origem.pedido p
join dados_de_origem.pagamento g on g.pedido_id = p.id
where (p.momento_compra at time zone 'America/Sao_Paulo')::date between %s and %s
"""


def _inicio_do_intervalo(dia: date, agrupamento: str) -> date:
    if agrupamento == "dia":
        return dia
    if agrupamento == "semana":
        return dia - timedelta(days=dia.weekday())
    return dia.replace(day=1)


def _intervalos(inicio: date, fim: date, agrupamento: str) -> list[date]:
    """O início de cada intervalo que toca o período, em ordem, tenha pedidos ou não."""
    inicios = []
    dia = inicio
    while dia <= fim:
        primeiro = _inicio_do_intervalo(dia, agrupamento)
        if not inicios or inicios[-1] != primeiro:
            inicios.append(primeiro)
        dia += timedelta(days=1)
    return inicios


def _na_origem(conexao, periodo: str) -> list[dict]:
    inicio, fim, agrupamento = PERIODOS[periodo]
    pedidos: Counter[date] = Counter()
    receita: dict[date, Decimal] = {}
    for dia, situacao, valor in conexao.execute(_PEDIDOS_NA_ORIGEM, (inicio, fim)):
        intervalo = _inicio_do_intervalo(dia, agrupamento)
        pedidos[intervalo] += 1
        if situacao == "Aprovado":
            receita[intervalo] = receita.get(intervalo, Decimal(0)) + valor
    return [
        {"inicio": i, "pedidos": pedidos[i], "receita": receita.get(i, Decimal(0))}
        for i in _intervalos(inicio, fim, agrupamento)
    ]


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.VENDAS)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_agrupamento_segue_o_periodo(respostas, periodo):
    resposta = respostas[periodo]

    assert resposta.status_code == 200
    assert resposta.json()["agrupamento"] == PERIODOS[periodo][2]


@pytest.mark.parametrize("periodo", PERIODOS)
def test_pontos_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    esperado = _na_origem(conexao_dono, periodo)
    pontos = respostas[periodo].json()["pontos"]

    assert [p["inicio"] for p in pontos] == [e["inicio"].isoformat() for e in esperado]
    assert [p["pedidos"] for p in pontos] == [e["pedidos"] for e in esperado]
    assert [Decimal(str(p["receita"])) for p in pontos] == [e["receita"] for e in esperado]


def test_quantidade_de_pontos_de_cada_periodo(respostas):
    """30 dias, 13 semanas (a primeira começa na segunda 31/08), 12 e 24 meses."""
    quantidades = {periodo: len(r.json()["pontos"]) for periodo, r in respostas.items()}

    assert quantidades == {"30d": 30, "90d": 14, "12m": 12, "24m": 24}


def test_a_semana_comeca_na_segunda(respostas):
    for ponto in respostas["90d"].json()["pontos"]:
        assert date.fromisoformat(ponto["inicio"]).weekday() == 0, ponto["inicio"]


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.VENDAS))

    assert resposta.json() == respostas["12m"].json()


def test_resposta_tem_numeros_crus_e_nenhum_identificador(respostas):
    corpo = respostas["12m"].json()

    assert set(corpo) == {"agrupamento", "pontos"}
    for ponto in corpo["pontos"]:
        assert set(ponto) == {"inicio", "pedidos", "receita"}
        assert isinstance(ponto["pedidos"], int)
        assert isinstance(ponto["receita"], int | float)
    texto = respostas["12m"].text
    for proibido in ("cliente", "_id", "dados_de_origem", "vendas."):
        assert proibido not in texto
