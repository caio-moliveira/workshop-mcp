"""A camada de leitura de Vendas: o papel de Vendas lê só a própria camada (ADR 0002)."""

import psycopg
import pytest
from apoio import (
    conectar_como_dono,
    conectar_como_vendas,
    rodar_carga,
    tabelas_dos_dados_de_origem,
)

# O contrato da camada: as views e suas colunas, em ordem.
COLUNAS_DA_CAMADA = {
    "pedido": [
        "id",
        "momento_compra",
        "cliente_id",
        "cliente_cidade",
        "cliente_uf",
        "lojista_id",
        "lojista_nome",
        "lojista_uf",
        "rota",
        "valor_frete",
    ],
    "item_pedido": [
        "pedido_id",
        "numero",
        "produto_id",
        "produto_nome",
        "categoria",
        "quantidade",
        "preco_unitario",
    ],
    "pagamento": ["pedido_id", "forma", "parcelas", "valor", "situacao"],
    "entrega": ["pedido_id", "data_prometida", "data_entrega", "situacao"],
}


@pytest.fixture
def conexao_vendas():
    with conectar_como_vendas() as conexao:
        yield conexao


@pytest.fixture
def conexao_vendas_em_modo_de_escrita():
    """Sessão que pede transações de escrita: só os privilégios podem barrar a escrita."""
    with conectar_como_vendas() as conexao:
        conexao.execute("set default_transaction_read_only = off")
        yield conexao


def _colunas_por_view(conexao) -> dict[str, list[str]]:
    colunas: dict[str, list[str]] = {}
    for view, coluna in conexao.execute(
        "select table_name, column_name from information_schema.columns"
        " where table_schema = 'vendas' order by table_name, ordinal_position"
    ):
        colunas.setdefault(view, []).append(coluna)
    return colunas


def test_a_camada_tem_exatamente_as_views_e_colunas_do_contrato(conexao_dono):
    assert _colunas_por_view(conexao_dono) == COLUNAS_DA_CAMADA


@pytest.mark.parametrize("view", sorted(COLUNAS_DA_CAMADA))
def test_vendas_le_cada_view_da_propria_camada(conexao_vendas, view):
    linhas = conexao_vendas.execute(f"select count(*) from vendas.{view}").fetchone()[0]

    assert linhas > 0


def test_vendas_e_recusado_em_todas_as_tabelas_dos_dados_de_origem(conexao_vendas, conexao_dono):
    tabelas = tabelas_dos_dados_de_origem(conexao_dono)
    assert tabelas

    for tabela in sorted(tabelas):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conexao_vendas.execute(f"select 1 from dados_de_origem.{tabela} limit 1")


@pytest.mark.parametrize(
    "comando",
    [
        "insert into vendas.pagamento (pedido_id, forma, parcelas, valor, situacao)"
        " values (999999, 'Pix', 1, 10, 'Aprovado')",
        "update vendas.entrega set situacao = 'Entregue no prazo'",
        "delete from vendas.pagamento",
        "create table vendas.intrusa (id int)",
        "create table public.intrusa (id int)",
        "create temporary table intrusa (id int)",
        "create schema intrusa",
        "select lo_create(0)",
        "select lo_creat(-1)",
        "select lo_from_bytea(0, 'intruso'::bytea)",
    ],
)
def test_vendas_nao_consegue_escrever_nem_criar_nada(conexao_vendas_em_modo_de_escrita, comando):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conexao_vendas_em_modo_de_escrita.execute(comando)


def test_sessao_de_vendas_comeca_somente_leitura(conexao_vendas):
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        conexao_vendas.execute("create temporary table intrusa (id int)")


def test_vendas_so_enxerga_as_views_da_propria_camada(conexao_vendas):
    visiveis = conexao_vendas.execute(
        """
        select table_schema, table_name from information_schema.tables
        where table_schema not in ('pg_catalog', 'information_schema')
        order by 1, 2
        """
    ).fetchall()

    assert visiveis == [("vendas", view) for view in sorted(COLUNAS_DA_CAMADA)]


def test_vendas_nao_conecta_em_nenhum_outro_banco_do_servidor(conexao_dono):
    outros = [
        linha[0]
        for linha in conexao_dono.execute(
            "select datname from pg_database"
            " where datallowconn and datname <> current_database() order by 1"
        )
    ]
    assert "postgres" in outros

    for banco in outros:
        with pytest.raises(psycopg.OperationalError, match="permission denied"):
            conectar_como_vendas(banco)


def test_camada_nao_expoe_dados_pessoais_de_clientes_nem_avaliacoes_nem_canal(conexao_dono):
    # Busca por trecho do nome, para pegar variações como cliente_email ou cpf_cliente.
    trechos_proibidos = ("email", "cpf", "cnpj", "documento", "endereco", "nota", "comentario")
    colunas = [coluna for lista in _colunas_por_view(conexao_dono).values() for coluna in lista]
    nomes_permitidos = {"lojista_nome", "produto_nome"}

    assert not [c for c in colunas if any(trecho in c for trecho in trechos_proibidos)]
    assert not [c for c in colunas if "nome" in c and c not in nomes_permitidos]
    assert not [c for c in colunas if "canal" in c]


def test_vendas_calcula_os_indicadores_do_painel_so_com_a_propria_camada(
    conexao_vendas, conexao_dono
):
    na_camada = conexao_vendas.execute(
        """
        select
            (select count(*) from vendas.pedido),
            (select sum(valor) from vendas.pagamento where situacao = 'Aprovado'),
            (select count(*) from vendas.pagamento where situacao = 'Aprovado'),
            (select count(*) from vendas.entrega where situacao = 'Entregue com atraso')
        """
    ).fetchone()
    na_origem = conexao_dono.execute(
        """
        select
            (select count(*) from dados_de_origem.pedido),
            (select sum(valor) from dados_de_origem.pagamento where situacao = 'Aprovado'),
            (select count(*) from dados_de_origem.pagamento where situacao = 'Aprovado'),
            (select count(*) from dados_de_origem.entrega where situacao = 'Entregue com atraso')
        """
    ).fetchone()

    assert na_camada == na_origem


def test_vendas_calcula_atrasos_por_rota_e_por_lojista(conexao_vendas, conexao_dono):
    por_rota_na_camada = conexao_vendas.execute(
        """
        select p.rota, count(*) from vendas.entrega e join vendas.pedido p on p.id = e.pedido_id
        where e.situacao = 'Entregue com atraso' group by 1 order by 2 desc, 1 limit 5
        """
    ).fetchall()
    por_rota_na_origem = conexao_dono.execute(
        """
        select l.uf || ' → ' || c.uf, count(*)
        from dados_de_origem.entrega e
        join dados_de_origem.pedido p on p.id = e.pedido_id
        join dados_de_origem.lojista l on l.id = p.lojista_id
        join dados_de_origem.cliente c on c.id = p.cliente_id
        where e.situacao = 'Entregue com atraso' group by 1 order by 2 desc, 1 limit 5
        """
    ).fetchall()
    por_lojista_na_camada = conexao_vendas.execute(
        """
        select p.lojista_id, p.lojista_nome, count(*)
        from vendas.entrega e join vendas.pedido p on p.id = e.pedido_id
        where e.situacao = 'Entregue com atraso' group by 1, 2 order by 3 desc, 1 limit 5
        """
    ).fetchall()

    assert por_rota_na_camada == por_rota_na_origem
    assert len(por_lojista_na_camada) == 5


def test_recarga_recria_a_camada_e_o_papel_com_as_mesmas_permissoes():
    rodar_carga()

    with conectar_como_vendas() as conexao:
        assert conexao.execute("select count(*) from vendas.pedido").fetchone()[0] > 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conexao.execute("select 1 from dados_de_origem.cliente limit 1")
    with conectar_como_dono() as conexao:
        assert conexao.execute("select count(*) from vendas.pedido").fetchone()[0] > 0
