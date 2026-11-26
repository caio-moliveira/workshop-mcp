"""A camada de leitura do Comercial: o papel do Comercial lê só a própria camada (ADR 0002).

O cruzamento com as camadas de Vendas e de Produtos e com os dados de origem fica na matriz de
papéis (test_matriz_de_papeis.py), e os bancos da auditoria e do histórico nos testes deles: todos
lêem os papéis de perfil do banco.
"""

import psycopg
import pytest
from apoio import conectar_como_dono, conectar_como_perfil, rodar_carga

from acesso import Perfil

# O contrato da camada: as views e suas colunas, em ordem.
COLUNAS_DA_CAMADA = {
    "lead": ["id", "empresa", "canal", "etapa", "data_criacao", "data_fechamento"],
    "referencia": ["data_referencia"],
}


@pytest.fixture
def conexao_comercial():
    with conectar_como_perfil(Perfil.COMERCIAL) as conexao:
        yield conexao


@pytest.fixture
def conexao_comercial_em_modo_de_escrita():
    """Sessão que pede transações de escrita: só os privilégios podem barrar a escrita."""
    with conectar_como_perfil(Perfil.COMERCIAL) as conexao:
        conexao.execute("set default_transaction_read_only = off")
        yield conexao


def _colunas_por_view(conexao) -> dict[str, list[str]]:
    colunas: dict[str, list[str]] = {}
    for view, coluna in conexao.execute(
        "select table_name, column_name from information_schema.columns"
        " where table_schema = 'comercial' order by table_name, ordinal_position"
    ):
        colunas.setdefault(view, []).append(coluna)
    return colunas


def test_a_camada_tem_exatamente_as_views_e_colunas_do_contrato(conexao_dono):
    assert _colunas_por_view(conexao_dono) == COLUNAS_DA_CAMADA


def test_camada_nao_traz_email_lojista_pedido_entrega_receita_produto_nem_avaliacao(conexao_dono):
    # Busca por trecho do nome, para pegar variações como lojista_id ou email_contato. Nada na
    # camada pode ligar um canal aos atrasos dos lojistas dele: isso é só da Diretoria.
    trechos_proibidos = (
        "email",
        "contato",
        "lojista",
        "cnpj",
        "cidade",
        "uf",
        "cliente",
        "pedido",
        "entrega",
        "atraso",
        "prazo",
        "valor",
        "receita",
        "pagamento",
        "produto",
        "categoria",
        "avaliacao",
        "nota",
    )
    colunas = [coluna for lista in _colunas_por_view(conexao_dono).values() for coluna in lista]

    assert not [c for c in colunas if any(trecho in c for trecho in trechos_proibidos)]


@pytest.mark.parametrize(
    "comando",
    [
        "insert into comercial.lead (id, empresa, canal, etapa, data_criacao)"
        " values (999999, 'Intrusa', 'Eventos', 'Novo', current_date)",
        "update comercial.lead set etapa = 'Perdido'",
        "delete from comercial.lead",
        "create table comercial.intrusa (id int)",
        "create table public.intrusa (id int)",
        "create temporary table intrusa (id int)",
        "create schema intrusa",
        "select lo_create(0)",
    ],
)
def test_comercial_nao_consegue_escrever_nem_criar_nada(
    conexao_comercial_em_modo_de_escrita, comando
):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conexao_comercial_em_modo_de_escrita.execute(comando)


def test_sessao_do_comercial_comeca_somente_leitura(conexao_comercial):
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        conexao_comercial.execute("create temporary table intrusa (id int)")


def test_comercial_so_enxerga_as_views_da_propria_camada(conexao_comercial):
    visiveis = conexao_comercial.execute(
        """
        select table_schema, table_name from information_schema.tables
        where table_schema not in ('pg_catalog', 'information_schema')
        order by 1, 2
        """
    ).fetchall()

    assert visiveis == [("comercial", view) for view in sorted(COLUNAS_DA_CAMADA)]


def test_comercial_nao_conecta_em_nenhum_outro_banco_do_servidor(conexao_dono):
    """Entre os outros estão os bancos da auditoria e do histórico."""
    outros = [
        linha[0]
        for linha in conexao_dono.execute(
            "select datname from pg_database"
            " where datallowconn and datname <> current_database() order by 1"
        )
    ]
    assert {"postgres", "auditoria", "historico"} <= set(outros)

    for banco in outros:
        with pytest.raises(psycopg.OperationalError, match="permission denied"):
            conectar_como_perfil(Perfil.COMERCIAL, banco)


@pytest.mark.parametrize("perfil", [Perfil.VENDAS, Perfil.PRODUTOS])
def test_vendas_e_produtos_sao_recusados_na_camada_do_comercial(perfil):
    with (
        conectar_como_perfil(perfil) as conexao,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        conexao.execute("select 1 from comercial.lead limit 1")


def test_a_camada_traz_todos_os_leads_com_a_empresa_o_canal_e_a_etapa(
    conexao_comercial, conexao_dono
):
    consulta = """
        select count(*), count(data_fechamento), count(distinct canal), count(distinct etapa),
               min(data_criacao), max(data_criacao), md5(string_agg({empresa}, '|' order by id))
        from {tabela}
    """
    na_camada = conexao_comercial.execute(
        consulta.format(empresa="empresa", tabela="comercial.lead")
    ).fetchone()
    na_origem = conexao_dono.execute(
        consulta.format(empresa="nome_empresa", tabela="dados_de_origem.lead")
    ).fetchone()

    assert na_camada == na_origem
    assert na_camada[2:4] == (5, 6)


def test_a_data_de_referencia_da_camada_e_a_dos_dados_de_origem(conexao_comercial, conexao_dono):
    consulta = "select data_referencia from {}.referencia"

    assert (
        conexao_comercial.execute(consulta.format("comercial")).fetchall()
        == conexao_dono.execute(consulta.format("dados_de_origem")).fetchall()
    )


def test_recarga_recria_a_camada_e_o_papel_com_as_mesmas_permissoes():
    rodar_carga()

    with conectar_como_perfil(Perfil.COMERCIAL) as conexao:
        assert conexao.execute("select count(*) from comercial.lead").fetchone()[0] > 0
        for de_outro in ("vendas.pedido", "produtos.avaliacao", "dados_de_origem.lead"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conexao.execute(f"select 1 from {de_outro} limit 1")
            conexao.rollback()
    with conectar_como_dono() as conexao:
        na_origem = conexao.execute("select count(*) from dados_de_origem.lead").fetchone()[0]
        assert conexao.execute("select count(*) from comercial.lead").fetchone()[0] == na_origem
