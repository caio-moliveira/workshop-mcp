"""GET /vendas/pedidos-recentes: os 20 pedidos mais recentes do período (RF-10).

As linhas esperadas vêm de uma consulta independente, feita com o papel dono nos dados de origem,
com os dias no horário de Brasília. O banco é o da carga padrão (data de referência 30/11/2026).
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from recusa import pedir

from acesso import Perfil

ROTA = "/vendas/pedidos-recentes"

PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}

_NA_ORIGEM = """
select
    p.id,
    p.momento_compra,
    c.cidade,
    c.uf,
    l.nome,
    l.uf || ' → ' || c.uf,
    g.valor,
    g.situacao,
    e.situacao
from dados_de_origem.pedido p
join dados_de_origem.cliente c on c.id = p.cliente_id
join dados_de_origem.lojista l on l.id = p.lojista_id
join dados_de_origem.pagamento g on g.pedido_id = p.id
left join dados_de_origem.entrega e on e.pedido_id = p.id
where (p.momento_compra at time zone 'America/Sao_Paulo')::date between %s and %s
order by p.momento_compra desc, p.id desc
limit 20
"""

CAMPOS = {
    "numero",
    "momento_compra",
    "cidade",
    "uf",
    "lojista",
    "rota",
    "valor",
    "pagamento",
    "entrega",
}


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.VENDAS)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


def _como_linha(pedido: dict) -> tuple:
    return (
        pedido["numero"],
        datetime.fromisoformat(pedido["momento_compra"]),
        pedido["cidade"],
        pedido["uf"],
        pedido["lojista"],
        pedido["rota"],
        Decimal(str(pedido["valor"])),
        pedido["pagamento"],
        pedido["entrega"],
    )


@pytest.mark.parametrize("periodo", PERIODOS)
def test_pedidos_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    resposta = respostas[periodo]
    esperado = conexao_dono.execute(_NA_ORIGEM, PERIODOS[periodo]).fetchall()

    assert resposta.status_code == 200
    assert len(esperado) == 20
    assert [_como_linha(p) for p in resposta.json()["pedidos"]] == [tuple(e) for e in esperado]


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


@pytest.mark.parametrize("periodo", PERIODOS)
def test_nenhum_identificador_nem_dado_pessoal_de_cliente(respostas, conexao_dono, periodo):
    resposta = respostas[periodo]
    pedidos = resposta.json()["pedidos"]
    dados_pessoais = conexao_dono.execute(
        """
        select c.nome, c.email, c.cpf, c.endereco
        from dados_de_origem.pedido p
        join dados_de_origem.cliente c on c.id = p.cliente_id
        where p.id = any(%s)
        """,
        ([p["numero"] for p in pedidos],),
    ).fetchall()

    assert all(set(p) == CAMPOS for p in pedidos)
    for proibido in ("cliente", "_id", "dados_de_origem", "vendas."):
        assert proibido not in resposta.text
    assert dados_pessoais
    for linha in dados_pessoais:
        for dado in linha:
            assert dado not in resposta.text
