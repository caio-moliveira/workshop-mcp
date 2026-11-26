"""A camada de leitura da Diretoria: já agregada, com o período como coluna (ADR 0011).

O contrato vale para toda view do esquema `diretoria`, lida do banco: uma view nova entra nestes
testes sem mudar nenhum deles. Fora a da data de referência, toda view tem uma linha por grupo,
com o período e a contagem do grupo em toda linha, e toda coluna de texto é uma dimensão fechada.
O cruzamento com as camadas dos outros perfis e com os dados de origem fica na matriz de papéis
(test_matriz_de_papeis.py), e os bancos da auditoria e do histórico nos testes deles.
"""

import psycopg
import pytest
from apoio import camadas_de_leitura, conectar_como_perfil, rodar_carga

from acesso import Perfil
from consultas.diretoria import DIMENSOES

ESQUEMA = "diretoria"
# A única view que não é de indicadores: o último dia coberto pelos dados.
REFERENCIA = "referencia"
# A contagem do grupo sobre o qual o número da linha foi calculado.
CONTAGEM = "contagem"

# Nada que identifique ou localize um cliente, lojista, lead ou produto, nem texto escrito por
# clientes (RF-05). Trechos do nome, para pegar variações como cliente_id ou email_contato.
TRECHOS_PROIBIDOS = (
    "nome",
    "email",
    "e_mail",
    "cpf",
    "cnpj",
    "documento",
    "endereco",
    "logradouro",
    "cep",
    "cidade",
    "comentario",
)
# Palavras inteiras do nome, separadas por "_": "uf" e "id" aparecem dentro de outras palavras.
PALAVRAS_PROIBIDAS = ("id", "uf", "estado")


def _colunas_por_view(conexao) -> dict[str, dict[str, str]]:
    """As colunas de cada view do esquema, com o tipo de dado de cada uma."""
    colunas: dict[str, dict[str, str]] = {}
    for view, coluna, tipo in conexao.execute(
        "select table_name, column_name, data_type from information_schema.columns"
        " where table_schema = %s order by table_name, ordinal_position",
        (ESQUEMA,),
    ):
        colunas.setdefault(view, {})[coluna] = tipo
    return colunas


@pytest.fixture
def views_de_indicadores(conexao_dono) -> dict[str, dict[str, str]]:
    """As colunas de cada view do esquema, menos a da data de referência."""
    views = _colunas_por_view(conexao_dono)
    views.pop(REFERENCIA, None)
    assert views
    return views


@pytest.fixture
def conexao_diretoria():
    with conectar_como_perfil(Perfil.DIRETORIA) as conexao:
        yield conexao


@pytest.fixture
def conexao_diretoria_em_modo_de_escrita():
    """Sessão que pede transações de escrita: só os privilégios podem barrar a escrita."""
    with conectar_como_perfil(Perfil.DIRETORIA) as conexao:
        conexao.execute("set default_transaction_read_only = off")
        yield conexao


def test_a_camada_tem_a_referencia_e_ao_menos_a_view_dos_indicadores(conexao_dono):
    views = _colunas_por_view(conexao_dono)

    assert views[REFERENCIA] == {"data_referencia": "date"}
    assert "indicadores" in views
    # Só views comuns: nada materializado, que pediria um passo depois da recarga (ADR 0011).
    tipos = conexao_dono.execute(
        "select distinct c.relkind from pg_class c join pg_namespace n on n.oid = c.relnamespace"
        " where n.nspname = %s",
        (ESQUEMA,),
    ).fetchall()
    assert tipos == [("v",)]


def test_nenhuma_coluna_identifica_localiza_ou_traz_comentario(conexao_dono):
    colunas = [c for colunas in _colunas_por_view(conexao_dono).values() for c in colunas]
    assert colunas

    proibidas = [
        coluna
        for coluna in colunas
        if any(trecho in coluna for trecho in TRECHOS_PROIBIDOS)
        or set(coluna.split("_")) & set(PALAVRAS_PROIBIDAS)
    ]
    assert proibidas == []


def test_toda_view_de_indicadores_traz_o_periodo_e_a_contagem_do_grupo(views_de_indicadores):
    for view, colunas in views_de_indicadores.items():
        assert "periodo" in colunas, view
        assert colunas.get(CONTAGEM) == "bigint", view


def test_nenhuma_linha_tem_contagem_1_nos_dados_da_carga(conexao_diretoria, views_de_indicadores):
    """Sem regra de supressão: a garantia de que nenhum grupo é um registro só é este teste."""
    for view in views_de_indicadores:
        linhas, com_um = conexao_diretoria.execute(
            f"select count(*), count(*) filter (where {CONTAGEM} = 1) from {ESQUEMA}.{view}"
        ).fetchone()

        assert linhas > 0, view
        assert com_um == 0, view


def test_toda_coluna_de_texto_e_uma_dimensao_fechada_com_os_valores_da_enumeracao(
    conexao_diretoria, views_de_indicadores
):
    """Um nome de lojista ou de produto seria uma coluna de texto fora das dimensões."""
    for view, colunas in views_de_indicadores.items():
        de_texto = [coluna for coluna, tipo in colunas.items() if tipo == "text"]

        assert set(de_texto) <= set(DIMENSOES), view
        for dimensao in de_texto:
            valores = {
                linha[0]
                for linha in conexao_diretoria.execute(
                    f"select distinct {dimensao} from {ESQUEMA}.{view}"
                )
            }
            assert valores == set(DIMENSOES[dimensao]), f"{view}.{dimensao}"


def test_toda_view_tem_uma_linha_por_periodo_e_grupo(conexao_diretoria, views_de_indicadores):
    """O grupo de uma linha são as colunas de texto (as dimensões) e as de data (o ponto)."""
    for view, colunas in views_de_indicadores.items():
        chave = [c for c, tipo in colunas.items() if tipo in ("text", "date")]

        linhas, distintas = conexao_diretoria.execute(
            f"select count(*), count(distinct ({', '.join(chave)})) from {ESQUEMA}.{view}"
        ).fetchone()

        assert linhas == distintas, view


def test_a_diretoria_le_a_data_de_referencia_dos_dados_de_origem(conexao_diretoria, conexao_dono):
    consulta = "select data_referencia from {}.referencia"

    assert (
        conexao_diretoria.execute(consulta.format(ESQUEMA)).fetchall()
        == conexao_dono.execute(consulta.format("dados_de_origem")).fetchall()
    )


@pytest.mark.parametrize(
    "comando",
    [
        "insert into diretoria.referencia (data_referencia) values (current_date)",
        # A da data de referência é a única view atualizável: nas agregadas, o banco recusaria
        # antes de olhar os privilégios, e a garantia não ficaria à prova.
        "update diretoria.referencia set data_referencia = current_date",
        "delete from diretoria.referencia",
        "create table diretoria.intrusa (id int)",
        "create table public.intrusa (id int)",
        "create temporary table intrusa (id int)",
        "create schema intrusa",
        "select lo_create(0)",
    ],
)
def test_diretoria_nao_consegue_escrever_nem_criar_nada(
    conexao_diretoria_em_modo_de_escrita, comando
):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conexao_diretoria_em_modo_de_escrita.execute(comando)


def test_em_toda_view_da_camada_a_diretoria_so_tem_o_privilegio_de_leitura(conexao_dono):
    privilegios = conexao_dono.execute(
        "select table_name, privilege_type from information_schema.role_table_grants"
        " where grantee = %s order by 1, 2",
        (Perfil.DIRETORIA.value,),
    ).fetchall()

    assert privilegios == [(view, "SELECT") for view in sorted(_colunas_por_view(conexao_dono))]


def test_sessao_da_diretoria_comeca_somente_leitura(conexao_diretoria):
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        conexao_diretoria.execute("create temporary table intrusa (id int)")


def test_diretoria_so_enxerga_as_views_da_propria_camada(conexao_diretoria, conexao_dono):
    """Nem as views de apoio de onde as da camada leem, que ficam fora do esquema."""
    visiveis = conexao_diretoria.execute(
        """
        select table_schema, table_name from information_schema.tables
        where table_schema not in ('pg_catalog', 'information_schema')
        order by 1, 2
        """
    ).fetchall()

    assert visiveis == [(ESQUEMA, view) for view in sorted(_colunas_por_view(conexao_dono))]


def test_diretoria_e_recusada_nas_views_de_apoio_da_camada(conexao_diretoria, conexao_dono):
    """As views da camada leem com o direito do dono; o papel não alcança de onde elas leem."""
    dependencias = [
        f"{esquema}.{tabela}"
        for esquema, tabela in conexao_dono.execute(
            """
            select distinct u.table_schema, u.table_name
            from information_schema.view_table_usage u
            where u.view_schema = %s and u.table_schema <> %s
            order by 1, 2
            """,
            (ESQUEMA, ESQUEMA),
        )
    ]
    assert dependencias

    for tabela in dependencias:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conexao_diretoria.execute(f"select 1 from {tabela} limit 1")
        conexao_diretoria.rollback()


def test_diretoria_nao_conecta_em_nenhum_outro_banco_do_servidor(conexao_dono):
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
            conectar_como_perfil(Perfil.DIRETORIA, banco)


@pytest.mark.parametrize("perfil", [Perfil.VENDAS, Perfil.PRODUTOS, Perfil.COMERCIAL], ids=str)
def test_os_outros_perfis_sao_recusados_em_toda_view_da_diretoria(conexao_dono, perfil):
    views = camadas_de_leitura(conexao_dono)[Perfil.DIRETORIA]
    assert views

    with conectar_como_perfil(perfil) as conexao:
        for view in views:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conexao.execute(f"select 1 from {ESQUEMA}.{view} limit 1")
            conexao.rollback()


def test_recarga_recria_a_camada_e_o_papel_com_as_mesmas_permissoes():
    rodar_carga()

    with conectar_como_perfil(Perfil.DIRETORIA) as conexao:
        assert conexao.execute("select count(*) from diretoria.indicadores").fetchone()[0] == 4
        for de_outro in (
            "vendas.pedido",
            "produtos.avaliacao",
            "comercial.lead",
            "dados_de_origem.pedido",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conexao.execute(f"select 1 from {de_outro} limit 1")
            conexao.rollback()
