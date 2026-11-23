"""A operação de vendas: clientes, pedidos, itens, pagamentos e entregas."""

from decimal import Decimal

import pytest
from apoio import contar
from referencias import REGIAO_POR_UF, cpf_valido


def _um(conexao, consulta: str):
    return conexao.execute(consulta).fetchone()[0]


@pytest.mark.parametrize(("tabela", "previsto"), [("cliente", 28500), ("pedido", 30000)])
def test_volume_fica_dentro_de_10_por_cento_do_previsto(conexao_dono, tabela, previsto):
    assert previsto * 0.9 <= contar(conexao_dono, tabela) <= previsto * 1.1


def test_todo_pedido_tem_um_lojista_um_pagamento_e_ao_menos_um_item(conexao_dono):
    incompletos = _um(
        conexao_dono,
        """
        select count(*) from dados_de_origem.pedido p
        where not exists (select 1 from dados_de_origem.lojista l where l.id = p.lojista_id)
           or (select count(*) from dados_de_origem.pagamento g where g.pedido_id = p.id) <> 1
           or not exists (select 1 from dados_de_origem.item_pedido i where i.pedido_id = p.id)
        """,
    )

    assert incompletos == 0


def test_itens_sao_produtos_do_lojista_do_pedido(conexao_dono):
    de_outro_lojista = _um(
        conexao_dono,
        """
        select count(*) from dados_de_origem.item_pedido i
        join dados_de_origem.pedido p on p.id = i.pedido_id
        join dados_de_origem.produto pr on pr.id = i.produto_id
        where pr.lojista_id <> p.lojista_id
        """,
    )

    assert de_outro_lojista == 0


def test_pedido_so_existe_depois_do_fechamento_do_lead_do_lojista(conexao_dono):
    antes_do_fechamento = _um(
        conexao_dono,
        """
        select count(*) from dados_de_origem.pedido p
        join dados_de_origem.lead l on l.lojista_id = p.lojista_id
        where p.momento_compra::date <= l.data_fechamento
        """,
    )

    assert antes_do_fechamento == 0


def test_pagamento_tem_forma_e_parcelas_coerentes(conexao_dono):
    formas = dict(
        conexao_dono.execute(
            "select forma, max(parcelas) from dados_de_origem.pagamento group by forma"
        ).fetchall()
    )
    parcelas_invalidas = _um(
        conexao_dono,
        """
        select count(*) from dados_de_origem.pagamento
        where parcelas not between 1 and 12 or (forma <> 'Cartão de crédito' and parcelas <> 1)
        """,
    )

    assert set(formas) == {"Cartão de crédito", "Pix", "Boleto"}
    assert formas["Cartão de crédito"] > 1
    assert parcelas_invalidas == 0


def test_poucos_por_cento_dos_pagamentos_sao_recusados(conexao_dono):
    proporcao = _um(
        conexao_dono,
        "select avg((situacao = 'Recusado')::int) from dados_de_origem.pagamento",
    )

    assert 0.01 <= proporcao <= 0.08


def test_pagamento_recusado_nao_gera_entrega_e_aprovado_gera(conexao_dono):
    incoerentes = _um(
        conexao_dono,
        """
        select count(*) from dados_de_origem.pagamento g
        left join dados_de_origem.entrega e on e.pedido_id = g.pedido_id
        where (g.situacao = 'Recusado') = (e.pedido_id is not null)
        """,
    )

    assert incoerentes == 0


def test_entrega_real_e_posterior_a_compra(conexao_dono):
    antes_da_compra = _um(
        conexao_dono,
        """
        select count(*) from dados_de_origem.entrega e
        join dados_de_origem.pedido p on p.id = e.pedido_id
        where e.data_entrega <= p.momento_compra::date
           or e.data_prometida <= p.momento_compra::date
        """,
    )

    assert antes_da_compra == 0


def test_situacao_da_entrega_corresponde_as_datas(conexao_dono):
    # Com a data de referência inicial, 30/11/2026.
    incoerentes = _um(
        conexao_dono,
        """
        select count(*) from dados_de_origem.entrega
        where case situacao
            when 'Entregue no prazo' then not (data_entrega <= data_prometida)
            when 'Entregue com atraso' then not (data_entrega > data_prometida)
            when 'Em trânsito' then data_entrega is not null
                or data_prometida < date '2026-11-30'
            when 'Prazo vencido' then data_entrega is not null
                or data_prometida >= date '2026-11-30'
        end
        """,
    )

    assert incoerentes == 0


def test_existem_pedidos_em_transito_e_com_prazo_vencido(conexao_dono):
    situacoes = dict(
        conexao_dono.execute(
            "select situacao, count(*) from dados_de_origem.entrega group by situacao"
        ).fetchall()
    )

    assert situacoes.get("Em trânsito", 0) > 0
    assert situacoes.get("Prazo vencido", 0) > 0


def test_frete_cresce_com_a_distancia_da_rota(conexao_dono):
    mesmo_estado, para_o_norte = conexao_dono.execute(
        """
        select
            avg(p.valor_frete) filter (where c.uf = 'SP'),
            avg(p.valor_frete) filter (where c.uf in ('AM', 'RR', 'AP', 'AC', 'RO'))
        from dados_de_origem.pedido p
        join dados_de_origem.lojista l on l.id = p.lojista_id
        join dados_de_origem.cliente c on c.id = p.cliente_id
        where l.uf = 'SP'
        """
    ).fetchone()

    assert para_o_norte > mesmo_estado * Decimal("1.5")


def test_clientes_estao_em_estados_reais_com_mais_volume_no_sudeste(conexao_dono):
    por_uf = dict(
        conexao_dono.execute("select uf, count(*) from dados_de_origem.cliente group by uf")
    )
    por_regiao: dict[str, int] = {}
    for uf, quantidade in por_uf.items():
        regiao = REGIAO_POR_UF[uf]  # uma UF inexistente falha aqui
        por_regiao[regiao] = por_regiao.get(regiao, 0) + quantidade

    assert max(por_regiao, key=por_regiao.get) == "Sudeste"
    assert por_regiao["Sudeste"] / sum(por_regiao.values()) >= 0.4


def test_documentos_e_emails_de_clientes_sao_ficticios(conexao_dono):
    cpfs = [linha[0] for linha in conexao_dono.execute("select cpf from dados_de_origem.cliente")]
    emails_fora_do_dominio_reservado = _um(
        conexao_dono,
        "select count(*) from dados_de_origem.cliente where email not like '%.example'",
    )

    assert all(len(cpf) == 11 and cpf.isdigit() for cpf in cpfs)
    assert not any(cpf_valido(cpf) for cpf in cpfs)
    assert len(set(cpfs)) == len(cpfs)
    assert emails_fora_do_dominio_reservado == 0


def test_entrega_prometida_depois_da_referencia_so_em_transito_ou_entregue_no_prazo(conexao_dono):
    # Com a data de referência inicial, 30/11/2026. Quem recebeu antes da data prometida
    # pode ter uma promessa que ainda estava no futuro.
    situacoes = {
        linha[0]
        for linha in conexao_dono.execute(
            "select distinct situacao from dados_de_origem.entrega"
            " where data_prometida > date '2026-11-30'"
        )
    }

    assert situacoes <= {"Em trânsito", "Entregue no prazo"}
    assert "Em trânsito" in situacoes
