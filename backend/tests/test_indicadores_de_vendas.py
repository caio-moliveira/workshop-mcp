"""GET /vendas/indicadores: os quatro indicadores do período e do período anterior (RF-10).

Os valores esperados vêm de consultas independentes, feitas com o papel dono nos dados de origem,
com os dias no horário de Brasília. O banco é o da carga padrão (data de referência 30/11/2026).
"""

from datetime import date
from decimal import Decimal

import pytest
from recusa import pedir

from acesso import Perfil

ROTA = "/vendas/indicadores"

# Os períodos que terminam em 30/11/2026 e os anteriores de mesmo tamanho, contados à mão.
# Nos 24 meses, o anterior começaria em 12/2022, antes do início dos dados (12/2024).
PERIODOS = {
    "30d": ((date(2026, 11, 1), date(2026, 11, 30)), (date(2026, 10, 2), date(2026, 10, 31))),
    "90d": ((date(2026, 9, 2), date(2026, 11, 30)), (date(2026, 6, 4), date(2026, 9, 1))),
    "12m": ((date(2025, 12, 1), date(2026, 11, 30)), (date(2024, 12, 1), date(2025, 11, 30))),
    "24m": ((date(2024, 12, 1), date(2026, 11, 30)), None),
}

_NA_ORIGEM = """
select
    count(*),
    coalesce(sum(g.valor) filter (where g.situacao = 'Aprovado'), 0),
    count(*) filter (where e.situacao = 'Entregue com atraso'),
    count(*) filter (where e.situacao in ('Entregue no prazo', 'Entregue com atraso')),
    count(*) filter (where g.situacao = 'Aprovado')
from dados_de_origem.pedido p
join dados_de_origem.pagamento g on g.pedido_id = p.id
left join dados_de_origem.entrega e on e.pedido_id = p.id
where (p.momento_compra at time zone 'America/Sao_Paulo')::date between %s and %s
"""


def _na_origem(conexao, intervalo) -> dict:
    pedidos, receita, atrasos, entregues, aprovados = conexao.execute(
        _NA_ORIGEM, intervalo
    ).fetchone()
    return {
        "pedidos": pedidos,
        "receita": receita,
        "atrasos": atrasos,
        "taxa_de_atraso": atrasos / entregues,
        "taxa_de_aprovacao": aprovados / pedidos,
    }


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.VENDAS)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    (inicio, fim), _ = PERIODOS[periodo]
    resposta = respostas[periodo]

    assert resposta.status_code == 200
    assert resposta.json()["periodo"] == {"inicio": inicio.isoformat(), "fim": fim.isoformat()}


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.VENDAS))

    assert resposta.json() == respostas["12m"].json()


@pytest.mark.parametrize("periodo", PERIODOS)
def test_indicadores_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    atual, anterior = PERIODOS[periodo]
    corpo = respostas[periodo].json()
    esperado = _na_origem(conexao_dono, atual)

    assert corpo["pedidos_realizados"]["atual"] == esperado["pedidos"]
    assert Decimal(str(corpo["receita"]["atual"])) == esperado["receita"]
    assert corpo["taxa_de_atraso"]["atual"] == pytest.approx(esperado["taxa_de_atraso"])
    assert corpo["taxa_de_atraso"]["atrasos"] == esperado["atrasos"]
    assert corpo["taxa_de_aprovacao"]["atual"] == pytest.approx(esperado["taxa_de_aprovacao"])

    if anterior is None:
        for indicador in ("pedidos_realizados", "receita", "taxa_de_atraso", "taxa_de_aprovacao"):
            assert corpo[indicador]["anterior"] is None, indicador
        return
    esperado_antes = _na_origem(conexao_dono, anterior)
    assert corpo["pedidos_realizados"]["anterior"] == esperado_antes["pedidos"]
    assert Decimal(str(corpo["receita"]["anterior"])) == esperado_antes["receita"]
    assert corpo["taxa_de_atraso"]["anterior"] == pytest.approx(esperado_antes["taxa_de_atraso"])
    assert corpo["taxa_de_aprovacao"]["anterior"] == pytest.approx(
        esperado_antes["taxa_de_aprovacao"]
    )


def test_os_dias_seguem_o_horario_de_brasilia(conexao_dono, respostas):
    """Há pedidos da noite de 31/10 em Brasília que já são 01/11 em UTC: eles ficam fora dos
    30 dias, e a contagem só bate se o dia for o de Brasília."""
    da_noite = conexao_dono.execute(
        """
        select count(*) from dados_de_origem.pedido
        where (momento_compra at time zone 'UTC')::date = date '2026-11-01'
            and (momento_compra at time zone 'America/Sao_Paulo')::date = date '2026-10-31'
        """
    ).fetchone()[0]
    em_utc = conexao_dono.execute(
        """
        select count(*) from dados_de_origem.pedido
        where (momento_compra at time zone 'UTC')::date between date '2026-11-01'
            and date '2026-11-30'
        """
    ).fetchone()[0]
    assert da_noite > 0

    assert respostas["30d"].json()["pedidos_realizados"]["atual"] != em_utc


def test_resposta_tem_numeros_crus_e_nenhum_identificador(respostas):
    corpo = respostas["12m"].json()

    assert set(corpo) == {
        "periodo",
        "pedidos_realizados",
        "receita",
        "taxa_de_atraso",
        "taxa_de_aprovacao",
    }
    assert isinstance(corpo["pedidos_realizados"]["atual"], int)
    assert isinstance(corpo["receita"]["atual"], float)
    assert 0 < corpo["taxa_de_atraso"]["atual"] < 1
    assert 0 < corpo["taxa_de_aprovacao"]["atual"] < 1
    texto = respostas["12m"].text
    for proibido in ("cliente", "_id", "dados_de_origem", "vendas."):
        assert proibido not in texto
