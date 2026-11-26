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

# Os blocos dos fatores de recompra e os grupos de cada um, na ordem em que a resposta os traz.
# Os grupos sem desfecho não existem: o primeiro pedido em trânsito ou com prazo vencido, e o
# primeiro pedido sem avaliação.
GRUPOS_DOS_FATORES: dict[str, tuple[str, ...]] = {
    "primeira_entrega": ("No prazo", "Com atraso"),
    "primeira_nota": ("1 ou 2", "3", "4 ou 5"),
    "faixa_de_atraso": ("No prazo", "Até 7 dias", "Mais de 7 dias"),
}
_BLOCO_DE_SATISFACAO = "faixa_de_atraso"

# As dimensões fechadas da camada: cada coluna de texto de uma view é uma delas, e os valores que
# ela traz são exatamente os da enumeração.
DIMENSOES: dict[str, tuple[str, ...]] = {
    "periodo": tuple(periodo.value for periodo in Periodo),
    "canal": tuple(canal.value for canal in Canal),
    "bloco": tuple(GRUPOS_DOS_FATORES),
    "grupo": tuple(dict.fromkeys(g for grupos in GRUPOS_DOS_FATORES.values() for g in grupos)),
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
def fatores_de_recompra(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Os três blocos dos fatores de recompra do período, cada grupo com o tamanho dele.

    Na primeira entrega e na primeira nota, a taxa de recompra do cartão repartida pelo primeiro
    pedido aprovado do cliente, qualquer que seja a data dele. Na faixa de atraso, a satisfação
    das avaliações do período conforme a entrega do pedido avaliado.
    """
    linhas = {
        (bloco, grupo): (contagem, com_recompra, satisfacao)
        for bloco, grupo, contagem, com_recompra, satisfacao in conexao.execute(
            """
            select bloco, grupo, contagem, clientes_com_recompra, satisfacao
            from diretoria.fatores_de_recompra
            where periodo = %s
            """,
            (periodo.value,),
        )
    }
    resposta: dict = {"periodo": _datas_do(periodo, conexao).como_json()}
    for bloco, grupos in GRUPOS_DOS_FATORES.items():
        itens = []
        for grupo in grupos:
            contagem, com_recompra, satisfacao = linhas[(bloco, grupo)]
            if bloco == _BLOCO_DE_SATISFACAO:
                itens.append({"grupo": grupo, "avaliacoes": contagem, "satisfacao": satisfacao})
            else:
                itens.append(
                    {
                        "grupo": grupo,
                        "clientes": contagem,
                        "clientes_com_recompra": com_recompra,
                        "taxa_de_recompra": _razao(com_recompra, contagem),
                    }
                )
        resposta[bloco] = itens
    return resposta
