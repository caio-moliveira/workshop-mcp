"""As consultas da Diretoria. Leem só a camada de leitura da Diretoria, já agregada (ADR 0011).

Cada view da camada traz as linhas dos quatro períodos, com o período como coluna: a consulta só
filtra o período pedido e não agrega. As regras de data são as dos outros perfis: o pedido entra
no período pelo dia da compra no horário de Brasília, como em Vendas, e a avaliação pela data
dela, como em Produtos. As respostas trazem números crus e datas ISO; a formatação é do frontend.
"""

from datetime import date

import psycopg

from acesso import Perfil
from consultas.lead import Canal
from consultas.periodo import DatasDoPeriodo, Periodo, terminado_em
from consultas.registro import consulta

# As dimensões fechadas da camada: cada coluna de texto de uma view é uma delas, e os valores que
# ela traz são exatamente os da enumeração.
DIMENSOES: dict[str, tuple[str, ...]] = {
    "periodo": tuple(periodo.value for periodo in Periodo),
    "canal": tuple(canal.value for canal in Canal),
}


def _data_de_referencia(conexao: psycopg.Connection) -> date:
    return conexao.execute("select data_referencia from diretoria.referencia").fetchone()[0]


def _datas_do(periodo: Periodo, conexao: psycopg.Connection) -> DatasDoPeriodo:
    """As datas do período que termina na data de referência dos dados."""
    return terminado_em(periodo, _data_de_referencia(conexao))


def _razao(parte: int | None, todo: int | None) -> float | None:
    """A parte dividida pelo todo, ou `None` quando falta um dos dois ou o todo é zero."""
    if parte is None or not todo:
        return None
    return parte / todo


@consulta(Perfil.DIRETORIA)
def indicadores(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Do período e do anterior de mesmo tamanho: a receita, a taxa de recompra, a satisfação e a
    retenção, com as contagens de cada uma.

    O anterior é `None` quando começaria antes do início dos dados, como em Vendas: em 24 meses,
    nenhum indicador tem anterior. A retenção do período compara com o anterior e não existe em 24
    meses; a do anterior compara com o período de dois para trás e não existe em 12 nem em 24.
    """
    linha = conexao.execute(
        """
        select contagem, clientes_com_recompra, receita, avaliacoes, satisfacao, retidos,
               contagem_anterior, clientes_com_recompra_anterior, receita_anterior,
               satisfacao_anterior, retidos_anterior, contagem_de_dois_periodos_antes
        from diretoria.indicadores
        where periodo = %s
        """,
        (periodo.value,),
    ).fetchone()
    (
        clientes,
        com_recompra,
        receita,
        avaliacoes,
        satisfacao,
        retidos,
        clientes_antes,
        com_recompra_antes,
        receita_antes,
        satisfacao_antes,
        retidos_antes,
        clientes_de_dois_antes,
    ) = linha
    return {
        "periodo": _datas_do(periodo, conexao).como_json(),
        "receita": {
            "atual": float(receita),
            "anterior": None if receita_antes is None else float(receita_antes),
        },
        "taxa_de_recompra": {
            "atual": _razao(com_recompra, clientes),
            "anterior": _razao(com_recompra_antes, clientes_antes),
            "clientes_com_recompra": com_recompra,
            "clientes": clientes,
        },
        "satisfacao": {
            "atual": satisfacao,
            "anterior": satisfacao_antes,
            "avaliacoes": avaliacoes,
        },
        "retencao": {
            "atual": _razao(retidos, clientes_antes),
            "anterior": _razao(retidos_antes, clientes_de_dois_antes),
            "retidos": retidos,
            "clientes_do_periodo_anterior": clientes_antes,
        },
    }


@consulta(Perfil.DIRETORIA)
def resumo(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Os cinco canais do lojista, do de maior taxa de atraso do período para o de menor.

    O canal é o do lead que originou o lojista. De cada um: os pedidos, a receita e a taxa de
    atraso dos pedidos dos lojistas do canal, com as regras de Vendas; a satisfação das avaliações
    desses pedidos, com a regra de data de Produtos; e a taxa de recompra dos clientes que contam
    no canal, o do lojista do primeiro pedido aprovado de cada um. As contagens vão ao lado das
    taxas. Uma taxa é `None` quando a contagem de que ela depende é zero, e o canal de taxa de
    atraso vazia vai para o fim; no empate, vem antes o de mais pedidos e depois o de nome menor.
    """
    linhas = conexao.execute(
        """
        select canal, contagem, receita, entregues, atrasos, avaliacoes, satisfacao, clientes,
               clientes_com_recompra
        from diretoria.resumo
        where periodo = %s
        order by atrasos::float / nullif(entregues, 0) desc nulls last, contagem desc, canal
        """,
        (periodo.value,),
    ).fetchall()
    return {
        "periodo": _datas_do(periodo, conexao).como_json(),
        "canais": [
            {
                "canal": canal,
                "pedidos": pedidos,
                "receita": float(receita),
                "taxa_de_atraso": _razao(atrasos, entregues),
                "entregues": entregues,
                "atrasos": atrasos,
                "satisfacao": satisfacao,
                "avaliacoes": avaliacoes,
                "taxa_de_recompra": _razao(com_recompra, clientes),
                "clientes": clientes,
                "clientes_com_recompra": com_recompra,
            }
            for (
                canal,
                pedidos,
                receita,
                entregues,
                atrasos,
                avaliacoes,
                satisfacao,
                clientes,
                com_recompra,
            ) in linhas
        ],
    }
