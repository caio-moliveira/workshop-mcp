"""Padrões 1, 2, 5 e 6 do PRD de dados, medidos só pelo que está nos dados.

Os testes leem o banco carregado com a configuração padrão (data de referência 30/11/2026).
O deslocamento da janela com outra data de referência é testado em test_determinismo.py.
"""

import math

from apoio import valor
from referencias import REGIAO_POR_UF


def test_padrao_1_recompra_baixa(conexao_dono):
    recompra = valor(
        conexao_dono,
        """
        select avg((aprovados >= 2)::int) from (
            select p.cliente_id, count(*) as aprovados
            from dados_de_origem.pedido p
            join dados_de_origem.pagamento g on g.pedido_id = p.id and g.situacao = 'Aprovado'
            group by p.cliente_id
        ) por_cliente
        """,
    )

    assert 0.04 <= recompra <= 0.06


def test_padrao_2_cerca_de_10_por_cento_dos_pedidos_entregues_atrasam(conexao_dono):
    taxa = valor(
        conexao_dono,
        """
        select avg((situacao = 'Entregue com atraso')::int) from dados_de_origem.entrega
        where situacao in ('Entregue no prazo', 'Entregue com atraso')
        """,
    )

    assert 0.09 <= taxa <= 0.11


def _parcela_dos_atrasos_no_decil_superior(conexao, agrupamento: str, juncao: str) -> float:
    return valor(
        conexao,
        f"""
        with atrasos as (
            select {agrupamento} as grupo, count(*) as quantidade
            from dados_de_origem.entrega e
            join dados_de_origem.pedido p on p.id = e.pedido_id
            {juncao}
            where e.situacao = 'Entregue com atraso'
            group by 1
        ),
        grupos as (
            select count(distinct {agrupamento}) as total
            from dados_de_origem.pedido p {juncao}
        )
        select sum(quantidade)::float / (select sum(quantidade) from atrasos)
        from (
            select quantidade from atrasos order by quantidade desc
            limit (select ceil(total * 0.1) from grupos)
        ) decil_superior
        """,
    )


def test_padrao_2_os_10_por_cento_de_lojistas_que_mais_atrasam_respondem_pela_metade(
    conexao_dono,
):
    parcela = _parcela_dos_atrasos_no_decil_superior(conexao_dono, "p.lojista_id", "")

    assert parcela >= 0.5


def test_padrao_2_os_10_por_cento_de_rotas_que_mais_atrasam_respondem_pela_metade(conexao_dono):
    parcela = _parcela_dos_atrasos_no_decil_superior(
        conexao_dono,
        "l.uf || '-' || c.uf",
        """
        join dados_de_origem.lojista l on l.id = p.lojista_id
        join dados_de_origem.cliente c on c.id = p.cliente_id
        """,
    )

    assert parcela >= 0.5


def test_padrao_2_atraso_dos_lojistas_que_mais_atrasam_vai_alem_do_volume(conexao_dono):
    # Complementa a regra acima: o grupo atrasa mais, não só vende mais.
    do_grupo, dos_demais = conexao_dono.execute(
        """
        with por_lojista as (
            select p.lojista_id,
                count(*) filter (where e.situacao = 'Entregue com atraso') as atrasos,
                count(*) as entregues
            from dados_de_origem.entrega e
            join dados_de_origem.pedido p on p.id = e.pedido_id
            where e.situacao in ('Entregue no prazo', 'Entregue com atraso')
            group by p.lojista_id
        ),
        ordenados as (
            select *, row_number() over (order by atrasos desc, lojista_id) as posicao,
                count(*) over () as total
            from por_lojista
        )
        select
            sum(atrasos) filter (where posicao <= ceil(total * 0.1))::float
                / sum(entregues) filter (where posicao <= ceil(total * 0.1)),
            sum(atrasos) filter (where posicao > ceil(total * 0.1))::float
                / sum(entregues) filter (where posicao > ceil(total * 0.1))
        from ordenados
        """
    ).fetchone()

    assert do_grupo >= 3 * dos_demais


def test_padrao_2_rotas_entre_regioes_atrasam_ao_menos_o_dobro_das_internas(conexao_dono):
    entregas = conexao_dono.execute(
        """
        select l.uf, c.uf, e.situacao = 'Entregue com atraso'
        from dados_de_origem.entrega e
        join dados_de_origem.pedido p on p.id = e.pedido_id
        join dados_de_origem.lojista l on l.id = p.lojista_id
        join dados_de_origem.cliente c on c.id = p.cliente_id
        where e.situacao in ('Entregue no prazo', 'Entregue com atraso')
        """
    ).fetchall()
    internas = [atrasou for origem, destino, atrasou in entregas if origem == destino]
    entre_regioes = [
        atrasou
        for origem, destino, atrasou in entregas
        if REGIAO_POR_UF[origem] != REGIAO_POR_UF[destino]
    ]

    assert sum(entre_regioes) / len(entre_regioes) >= 2 * sum(internas) / len(internas)


def test_padrao_5_lojistas_de_midia_paga_atrasam_ao_menos_o_dobro(conexao_dono):
    do_canal, dos_demais = conexao_dono.execute(
        """
        select
            avg((e.situacao = 'Entregue com atraso')::int) filter (where l.canal = 'Mídia paga'),
            avg((e.situacao = 'Entregue com atraso')::int) filter (where l.canal <> 'Mídia paga')
        from dados_de_origem.entrega e
        join dados_de_origem.pedido p on p.id = e.pedido_id
        join dados_de_origem.lead l on l.lojista_id = p.lojista_id
        where e.situacao in ('Entregue no prazo', 'Entregue com atraso')
        """
    ).fetchone()

    assert do_canal >= 2 * dos_demais


def _pedidos_por_mes(conexao) -> list[tuple[int, int, int]]:
    """(índice do mês na janela, mês do ano, pedidos), com a janela de 12/2024 a 11/2026."""
    return conexao.execute(
        """
        select
            (extract(year from momento_compra) - 2024) * 12
                + extract(month from momento_compra) - 12,
            extract(month from momento_compra),
            count(*)
        from dados_de_origem.pedido
        group by 1, 2
        order by 1
        """
    ).fetchall()


def test_padrao_6_novembro_e_dezembro_tem_pico(conexao_dono):
    meses = _pedidos_por_mes(conexao_dono)
    assert len(meses) == 24
    for ciclo in (0, 1):
        do_ciclo = [(mes, pedidos) for indice, mes, pedidos in meses if indice // 12 == ciclo]
        outros = [pedidos for mes, pedidos in do_ciclo if mes not in (11, 12)]
        media_dos_outros = sum(outros) / len(outros)
        for mes, pedidos in do_ciclo:
            if mes in (11, 12):
                assert pedidos >= 1.5 * media_dos_outros, (ciclo, mes)


def test_padrao_6_crescimento_leve_mes_a_mes(conexao_dono):
    pontos = [
        (int(indice), math.log(pedidos))
        for indice, mes, pedidos in _pedidos_por_mes(conexao_dono)
        if mes not in (11, 12)
    ]
    n = len(pontos)
    media_x = sum(x for x, _ in pontos) / n
    media_y = sum(y for _, y in pontos) / n
    inclinacao = sum((x - media_x) * (y - media_y) for x, y in pontos) / sum(
        (x - media_x) ** 2 for x, _ in pontos
    )

    assert 0.01 <= math.exp(inclinacao) - 1 <= 0.03
