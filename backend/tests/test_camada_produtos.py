"""A camada de leitura de Produtos: o papel de Produtos lê só a própria camada (ADR 0002).

O cruzamento com a camada de Vendas e com os dados de origem fica na matriz de papéis
(test_matriz_de_papeis.py), e os bancos da auditoria e do histórico nos testes deles: todos lêem
os papéis de perfil do banco.
"""

import psycopg
import pytest
from apoio import conectar_como_dono, conectar_como_perfil, rodar_carga

from acesso import Perfil

# O contrato da camada: as views e suas colunas, em ordem.
COLUNAS_DA_CAMADA = {
    "produto": ["id", "nome", "categoria", "preco"],
    "avaliacao": ["id", "produto_id", "nota", "comentario", "data_avaliacao"],
    "referencia": ["data_referencia"],
}


@pytest.fixture
def conexao_produtos():
    with conectar_como_perfil(Perfil.PRODUTOS) as conexao:
        yield conexao


@pytest.fixture
def conexao_produtos_em_modo_de_escrita():
    """Sessão que pede transações de escrita: só os privilégios podem barrar a escrita."""
    with conectar_como_perfil(Perfil.PRODUTOS) as conexao:
        conexao.execute("set default_transaction_read_only = off")
        yield conexao


def _colunas_por_view(conexao) -> dict[str, list[str]]:
    colunas: dict[str, list[str]] = {}
    for view, coluna in conexao.execute(
        "select table_name, column_name from information_schema.columns"
        " where table_schema = 'produtos' order by table_name, ordinal_position"
    ):
        colunas.setdefault(view, []).append(coluna)
    return colunas


def test_a_camada_tem_exatamente_as_views_e_colunas_do_contrato(conexao_dono):
    assert _colunas_por_view(conexao_dono) == COLUNAS_DA_CAMADA


def test_camada_nao_traz_cliente_pedido_entrega_quantidade_receita_nem_lojista(conexao_dono):
    # Busca por trecho do nome, para pegar variações como cliente_id ou valor_pedido.
    trechos_proibidos = (
        "cliente",
        "pedido",
        "entrega",
        "atraso",
        "prazo",
        "quantidade",
        "valor",
        "receita",
        "pagamento",
        "lojista",
    )
    colunas = [coluna for lista in _colunas_por_view(conexao_dono).values() for coluna in lista]

    assert not [c for c in colunas if any(trecho in c for trecho in trechos_proibidos)]


@pytest.mark.parametrize(
    "comando",
    [
        "insert into produtos.avaliacao (id, produto_id, nota, data_avaliacao)"
        " values (999999, 1, 5, current_date)",
        "update produtos.avaliacao set nota = 1",
        "delete from produtos.avaliacao",
        "create table produtos.intrusa (id int)",
        "create table public.intrusa (id int)",
        "create temporary table intrusa (id int)",
        "create schema intrusa",
        "select lo_create(0)",
    ],
)
def test_produtos_nao_consegue_escrever_nem_criar_nada(
    conexao_produtos_em_modo_de_escrita, comando
):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conexao_produtos_em_modo_de_escrita.execute(comando)


def test_sessao_de_produtos_comeca_somente_leitura(conexao_produtos):
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        conexao_produtos.execute("create temporary table intrusa (id int)")


def test_produtos_so_enxerga_as_views_da_propria_camada(conexao_produtos):
    visiveis = conexao_produtos.execute(
        """
        select table_schema, table_name from information_schema.tables
        where table_schema not in ('pg_catalog', 'information_schema')
        order by 1, 2
        """
    ).fetchall()

    assert visiveis == [("produtos", view) for view in sorted(COLUNAS_DA_CAMADA)]


def test_produtos_nao_conecta_em_nenhum_outro_banco_do_servidor(conexao_dono):
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
            conectar_como_perfil(Perfil.PRODUTOS, banco)


def test_a_camada_traz_o_catalogo_e_as_avaliacoes_inteiros(conexao_produtos, conexao_dono):
    na_camada = conexao_produtos.execute(
        """
        select
            (select count(*) from produtos.produto),
            (select count(*) from produtos.avaliacao),
            (select count(*) from produtos.avaliacao where comentario is not null),
            (select count(distinct categoria) from produtos.produto)
        """
    ).fetchone()
    na_origem = conexao_dono.execute(
        """
        select
            (select count(*) from dados_de_origem.produto),
            (select count(*) from dados_de_origem.avaliacao),
            (select count(*) from dados_de_origem.avaliacao where comentario is not null),
            (select count(*) from dados_de_origem.categoria)
        """
    ).fetchone()

    assert na_camada == na_origem
    assert na_camada[0] == 2000


def test_recarga_recria_a_camada_e_o_papel_com_as_mesmas_permissoes():
    rodar_carga()

    with conectar_como_perfil(Perfil.PRODUTOS) as conexao:
        assert conexao.execute("select count(*) from produtos.avaliacao").fetchone()[0] > 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conexao.execute("select 1 from vendas.pedido limit 1")
    with conectar_como_dono() as conexao:
        assert conexao.execute("select count(*) from produtos.produto").fetchone()[0] == 2000
