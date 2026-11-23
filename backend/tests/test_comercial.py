"""O lado comercial: leads, canais, etapas do funil e lojistas."""

import pytest
from apoio import contar
from referencias import REGIAO_POR_UF, cnpj_valido


@pytest.mark.parametrize(("tabela", "previsto"), [("lead", 1500), ("lojista", 300)])
def test_volume_fica_dentro_de_10_por_cento_do_previsto(conexao_dono, tabela, previsto):
    assert previsto * 0.9 <= contar(conexao_dono, tabela) <= previsto * 1.1


def test_todo_lojista_tem_exatamente_um_lead_fechado_com_canal_e_data(conexao_dono):
    lojistas_sem_um_lead_fechado = conexao_dono.execute(
        """
        select l.id
        from dados_de_origem.lojista l
        left join dados_de_origem.lead fechado
            on fechado.lojista_id = l.id
            and fechado.etapa = 'Fechado'
            and fechado.canal is not null
            and fechado.data_fechamento is not null
        group by l.id
        having count(fechado.id) <> 1
        """
    ).fetchall()

    assert lojistas_sem_um_lead_fechado == []


def test_lead_nao_fechado_nao_tem_data_de_fechamento_nem_lojista(conexao_dono):
    inconsistentes = conexao_dono.execute(
        """
        select count(*) from dados_de_origem.lead
        where etapa <> 'Fechado' and (data_fechamento is not null or lojista_id is not null)
        """
    ).fetchone()[0]

    assert inconsistentes == 0


def test_leads_nao_fechados_se_dividem_entre_perdido_e_etapas_abertas(conexao_dono):
    etapas = dict(
        conexao_dono.execute(
            "select etapa, count(*) from dados_de_origem.lead"
            " where etapa <> 'Fechado' group by etapa"
        ).fetchall()
    )

    assert etapas.get("Perdido", 0) > 0
    assert set(etapas) - {"Perdido"} == {"Novo", "Contatado", "Qualificado", "Proposta"}


def test_cerca_de_300_leads_fechados(conexao_dono):
    fechados = conexao_dono.execute(
        "select count(*) from dados_de_origem.lead where etapa = 'Fechado'"
    ).fetchone()[0]

    assert 270 <= fechados <= 330


def test_todos_os_cinco_canais_aparecem(conexao_dono):
    canais = {
        linha[0]
        for linha in conexao_dono.execute("select distinct canal from dados_de_origem.lead")
    }

    assert canais == {"Indicação", "Orgânico", "Mídia paga", "Eventos", "Prospecção ativa"}


def test_cerca_de_80_lojistas_fecharam_antes_do_inicio_da_janela_de_pedidos(conexao_dono):
    # Com a data de referência inicial (30/11/2026), a janela de 24 meses começa em 01/12/2024.
    antes_da_janela = conexao_dono.execute(
        "select count(*) from dados_de_origem.lead"
        " where etapa = 'Fechado' and data_fechamento < date '2024-12-01'"
    ).fetchone()[0]

    assert 72 <= antes_da_janela <= 88


def test_lojistas_estao_em_estados_reais_com_mais_volume_no_sudeste(conexao_dono):
    por_uf = dict(
        conexao_dono.execute("select uf, count(*) from dados_de_origem.lojista group by uf")
    )
    por_regiao: dict[str, int] = {}
    for uf, quantidade in por_uf.items():
        regiao = REGIAO_POR_UF[uf]  # uma UF inexistente falha aqui
        por_regiao[regiao] = por_regiao.get(regiao, 0) + quantidade

    assert max(por_regiao, key=por_regiao.get) == "Sudeste"
    assert por_regiao["Sudeste"] / sum(por_regiao.values()) >= 0.4


def test_cidades_conhecidas_aparecem_no_estado_certo(conexao_dono):
    pares = set(
        conexao_dono.execute("select distinct cidade, uf from dados_de_origem.lojista").fetchall()
    )

    assert ("São Paulo", "SP") in pares
    assert all(uf == "SP" for cidade, uf in pares if cidade == "São Paulo")


def test_nenhum_cnpj_de_lojista_e_valido_e_nenhum_se_repete(conexao_dono):
    cnpjs = [linha[0] for linha in conexao_dono.execute("select cnpj from dados_de_origem.lojista")]

    assert all(len(cnpj) == 14 and cnpj.isdigit() for cnpj in cnpjs)
    assert not any(cnpj_valido(cnpj) for cnpj in cnpjs)
    assert len(set(cnpjs)) == len(cnpjs)


def test_emails_de_leads_usam_dominio_reservado_para_exemplos(conexao_dono):
    fora_do_dominio_reservado = conexao_dono.execute(
        "select count(*) from dados_de_origem.lead where email_contato not like '%.example'"
    ).fetchone()[0]

    assert fora_do_dominio_reservado == 0
