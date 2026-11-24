"""GET /vendas/situacao-das-entregas: os pedidos do período em cada situação de entrega (RF-10).

As contagens esperadas vêm de uma consulta independente, feita com o papel dono nos dados de
origem, com os dias no horário de Brasília. O banco é o da carga padrão (data de referência
30/11/2026).
"""

from datetime import date

import pytest
from recusa import pedir

from acesso import Perfil

ROTA = "/vendas/situacao-das-entregas"

PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}

# As quatro situações, da entrega em aberto à entrega concluída.
SITUACOES = ["Em trânsito", "Prazo vencido", "Entregue no prazo", "Entregue com atraso"]

_NA_ORIGEM = """
select e.situacao, count(*)
from dados_de_origem.pedido p
join dados_de_origem.entrega e on e.pedido_id = p.id
where (p.momento_compra at time zone 'America/Sao_Paulo')::date between %s and %s
group by e.situacao
"""


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.VENDAS)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_contagens_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    resposta = respostas[periodo]
    esperado = dict(conexao_dono.execute(_NA_ORIGEM, PERIODOS[periodo]).fetchall())

    assert resposta.status_code == 200
    assert sum(esperado.values()) > 0
    assert resposta.json()["situacoes"] == [
        {"situacao": situacao, "pedidos": esperado.get(situacao, 0)} for situacao in SITUACOES
    ]


def test_as_quatro_situacoes_vem_sempre_na_mesma_ordem(respostas):
    """Uma situação sem pedido no período vem com zero, não some (o esperado acima usa 0)."""
    for resposta in respostas.values():
        assert [s["situacao"] for s in resposta.json()["situacoes"]] == SITUACOES


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    inicio, fim = PERIODOS[periodo]

    assert respostas[periodo].json()["periodo"] == {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
    }


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.VENDAS))

    assert resposta.json() == respostas["12m"].json()


def test_resposta_tem_numeros_crus_e_nenhum_identificador(respostas):
    corpo = respostas["12m"].json()

    assert set(corpo) == {"periodo", "situacoes"}
    for situacao in corpo["situacoes"]:
        assert set(situacao) == {"situacao", "pedidos"}
        assert isinstance(situacao["pedidos"], int)
    texto = respostas["12m"].text
    for proibido in ("cliente", "_id", "dados_de_origem", "vendas."):
        assert proibido not in texto
