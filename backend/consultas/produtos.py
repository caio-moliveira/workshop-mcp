"""As consultas de Produtos. Leem só a camada de leitura de Produtos (ADR 0002).

O período filtra pela data da avaliação; o catálogo não depende dele (glossário). As respostas
trazem números crus e datas ISO; a formatação é do frontend.
"""

from dataclasses import dataclass

import psycopg

from acesso import Perfil
from consultas.periodo import DatasDoPeriodo, Periodo, inicio_dos_dados, terminado_em
from consultas.registro import consulta

# Reclamação: avaliação com nota 1 ou 2 (glossário).
NOTA_MAXIMA_DA_RECLAMACAO = 2
# Produto mal avaliado: nota média abaixo disto nas avaliações do período...
NOTA_MEDIA_DO_MAL_AVALIADO = 3
# ...com pelo menos estas avaliações no período (glossário).
MINIMO_DE_AVALIACOES_DO_MAL_AVALIADO = 3
# Teto de linhas da lista de produtos mal avaliados (RF-25).
LIMITE_DE_MAL_AVALIADOS = 50

# A regra do produto mal avaliado, a mesma no indicador e na lista: um produto por linha, com a
# nota média e o número de avaliações no período.
_MAL_AVALIADOS = """
    select produto_id, avg(nota) as media, count(*) as quantas
    from produtos.avaliacao
    where data_avaliacao between %(inicio)s and %(fim)s
    group by produto_id
    having avg(nota) < %(media)s and count(*) >= %(minimo)s
"""


@dataclass(frozen=True)
class _Resumo:
    produtos_avaliados: int
    nota_media: float | None
    avaliacoes: int
    reclamacoes: int
    produtos_mal_avaliados: int


def _datas_do(periodo: Periodo, conexao: psycopg.Connection) -> DatasDoPeriodo:
    """As datas do período que termina na data de referência dos dados."""
    referencia = conexao.execute("select data_referencia from produtos.referencia").fetchone()[0]
    return terminado_em(periodo, referencia)


def _parametros(datas: DatasDoPeriodo) -> dict:
    return {
        "inicio": datas.inicio,
        "fim": datas.fim,
        "reclamacao": NOTA_MAXIMA_DA_RECLAMACAO,
        "media": NOTA_MEDIA_DO_MAL_AVALIADO,
        "minimo": MINIMO_DE_AVALIACOES_DO_MAL_AVALIADO,
    }


def _resumo(conexao: psycopg.Connection, datas: DatasDoPeriodo) -> _Resumo:
    linha = conexao.execute(
        f"""
        with do_periodo as (
            select produto_id, nota from produtos.avaliacao
            where data_avaliacao between %(inicio)s and %(fim)s
        )
        select
            (select count(distinct produto_id) from do_periodo),
            (select avg(nota)::float from do_periodo),
            (select count(*) from do_periodo),
            (select count(*) from do_periodo where nota <= %(reclamacao)s),
            (select count(*) from ({_MAL_AVALIADOS}) mal_avaliados)
        """,
        _parametros(datas),
    ).fetchone()
    return _Resumo(*linha)


@consulta(Perfil.PRODUTOS)
def indicadores(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """O tamanho do catálogo e, do período e do anterior: produtos avaliados, nota média,
    avaliações, reclamações e produtos mal avaliados.

    O anterior tem o mesmo tamanho e termina na véspera do início; é `None` quando começaria antes
    do início dos dados, como em Vendas. A nota média é `None` num período sem avaliações.
    """
    atual = _datas_do(periodo, conexao)
    datas_anteriores = atual.anterior(periodo)
    agora = _resumo(conexao, atual)
    antes = (
        _resumo(conexao, datas_anteriores)
        if datas_anteriores.inicio >= inicio_dos_dados(atual.fim)
        else None
    )
    catalogo = conexao.execute("select count(*) from produtos.produto").fetchone()[0]

    def par(indicador: str) -> dict:
        return {
            "atual": getattr(agora, indicador),
            "anterior": None if antes is None else getattr(antes, indicador),
        }

    return {
        "periodo": atual.como_json(),
        "catalogo": catalogo,
        "produtos_avaliados": par("produtos_avaliados"),
        "nota_media": par("nota_media"),
        "avaliacoes": par("avaliacoes"),
        "reclamacoes": par("reclamacoes"),
        "produtos_mal_avaliados": par("produtos_mal_avaliados"),
    }


@consulta(Perfil.PRODUTOS)
def mal_avaliados(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Os produtos mal avaliados do período, da pior nota média para a melhor, no máximo 50.

    Na mesma nota média, vem antes o produto com mais avaliações. O identificador do produto vem
    no resultado para pedir as avaliações dele.
    """
    datas = _datas_do(periodo, conexao)
    linhas = conexao.execute(
        f"""
        select p.id, p.nome, p.categoria, p.preco, m.media::float, m.quantas
        from ({_MAL_AVALIADOS}) m
        join produtos.produto p on p.id = m.produto_id
        order by m.media, m.quantas desc, p.id
        limit %(limite)s
        """,
        {**_parametros(datas), "limite": LIMITE_DE_MAL_AVALIADOS},
    ).fetchall()
    return {
        "periodo": datas.como_json(),
        "produtos": [
            {
                "produto": produto,
                "nome": nome,
                "categoria": categoria,
                "preco": float(preco),
                "nota_media": nota_media,
                "avaliacoes": avaliacoes,
            }
            for produto, nome, categoria, preco, nota_media, avaliacoes in linhas
        ],
    }


@consulta(Perfil.PRODUTOS)
def notas(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Quantas avaliações do período há em cada nota, de 1 a 5, com zero na nota sem avaliação."""
    datas = _datas_do(periodo, conexao)
    linhas = conexao.execute(
        """
        select n.nota, count(a.id)
        from generate_series(1, 5) as n(nota)
        left join produtos.avaliacao a
            on a.nota = n.nota and a.data_avaliacao between %s and %s
        group by n.nota
        order by n.nota
        """,
        (datas.inicio, datas.fim),
    ).fetchall()
    return {
        "periodo": datas.como_json(),
        "notas": [{"nota": nota, "avaliacoes": quantas} for nota, quantas in linhas],
    }


@consulta(Perfil.PRODUTOS)
def categorias(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Todas as categorias, da pior nota média do período para a melhor (empate pelo nome).

    De cada uma: os produtos do catálogo, que não dependem do período, e as avaliações, a nota
    média, as reclamações e a taxa de reclamação do período. Uma categoria sem avaliação no período
    vem por último, com nota média e taxa nulas.
    """
    datas = _datas_do(periodo, conexao)
    linhas = conexao.execute(
        """
        with do_periodo as (
            select produto_id, nota from produtos.avaliacao
            where data_avaliacao between %(inicio)s and %(fim)s
        )
        select
            p.categoria,
            count(distinct p.id),
            count(a.nota),
            avg(a.nota)::float,
            count(a.nota) filter (where a.nota <= %(reclamacao)s)
        from produtos.produto p
        left join do_periodo a on a.produto_id = p.id
        group by p.categoria
        order by avg(a.nota) asc nulls last, p.categoria
        """,
        {"inicio": datas.inicio, "fim": datas.fim, "reclamacao": NOTA_MAXIMA_DA_RECLAMACAO},
    ).fetchall()
    return {
        "periodo": datas.como_json(),
        "categorias": [
            {
                "categoria": categoria,
                "produtos": produtos_da_categoria,
                "avaliacoes": avaliacoes,
                "nota_media": nota_media,
                "reclamacoes": reclamacoes,
                "taxa_de_reclamacao": reclamacoes / avaliacoes if avaliacoes else None,
            }
            for categoria, produtos_da_categoria, avaliacoes, nota_media, reclamacoes in linhas
        ],
    }
