"""As consultas do painel de Vendas. Leem só a camada de leitura de Vendas (ADR 0002).

Todo pedido entra num período pelo dia do `momento_compra` no horário de Brasília. As respostas
trazem números crus e datas ISO; a formatação é do frontend.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import psycopg

from acesso import Perfil
from consultas.periodo import DatasDoPeriodo, Periodo, inicio_dos_dados, terminado_em
from consultas.registro import consulta

# O dia de um pedido, no fuso do negócio, venha a sessão com o fuso que vier.
DIA_DO_PEDIDO = "(p.momento_compra at time zone 'America/Sao_Paulo')::date"
# O pedido `p` é do período cujas datas vêm nos dois parâmetros seguintes, início e fim.
NO_PERIODO = f"{DIA_DO_PEDIDO} between %s and %s"

# A tabela do painel é limitada: sem paginação nem rota de detalhe.
LIMITE_DE_PEDIDOS_RECENTES = 20


@dataclass(frozen=True)
class _Resumo:
    pedidos: int
    receita: Decimal
    atrasos: int
    entregues: int
    aprovados: int

    @property
    def taxa_de_atraso(self) -> float | None:
        """Entregues com atraso ÷ entregues. Prazo vencido não entra (glossário)."""
        return self.atrasos / self.entregues if self.entregues else None

    @property
    def taxa_de_aprovacao(self) -> float | None:
        return self.aprovados / self.pedidos if self.pedidos else None


def _data_de_referencia(conexao: psycopg.Connection) -> date:
    return conexao.execute("select data_referencia from vendas.referencia").fetchone()[0]


def _datas_do(periodo: Periodo, conexao: psycopg.Connection) -> DatasDoPeriodo:
    """As datas do período que termina na data de referência dos dados."""
    return terminado_em(periodo, _data_de_referencia(conexao))


def _resumo(conexao: psycopg.Connection, datas: DatasDoPeriodo) -> _Resumo:
    linha = conexao.execute(
        f"""
        select
            count(*),
            coalesce(sum(g.valor) filter (where g.situacao = 'Aprovado'), 0),
            count(*) filter (where e.situacao = 'Entregue com atraso'),
            count(*) filter (where e.situacao in ('Entregue no prazo', 'Entregue com atraso')),
            count(*) filter (where g.situacao = 'Aprovado')
        from vendas.pedido p
        join vendas.pagamento g on g.pedido_id = p.id
        left join vendas.entrega e on e.pedido_id = p.id
        where {NO_PERIODO}
        """,
        (datas.inicio, datas.fim),
    ).fetchone()
    return _Resumo(*linha)


@consulta(Perfil.VENDAS)
def indicadores(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Pedidos realizados, receita, taxa de atraso e taxa de aprovação do período e do anterior.

    O anterior tem o mesmo tamanho e termina na véspera do início. É `None` quando começaria
    antes do início dos dados (os 24 meses que terminam na data de referência), onde não haveria
    com o que comparar.
    """
    atual = _datas_do(periodo, conexao)
    datas_anteriores = atual.anterior(periodo)
    agora = _resumo(conexao, atual)
    antes = (
        _resumo(conexao, datas_anteriores)
        if datas_anteriores.inicio >= inicio_dos_dados(atual.fim)
        else None
    )

    def par(indicador: Callable[[_Resumo], object]) -> dict:
        return {"atual": indicador(agora), "anterior": None if antes is None else indicador(antes)}

    return {
        "periodo": atual.como_json(),
        "pedidos_realizados": par(lambda r: r.pedidos),
        "receita": par(lambda r: float(r.receita)),
        "taxa_de_atraso": {**par(lambda r: r.taxa_de_atraso), "atrasos": agora.atrasos},
        "taxa_de_aprovacao": par(lambda r: r.taxa_de_aprovacao),
    }


# O nome de cada agrupamento da evolução, conforme o período, e a unidade de `date_trunc` dele. A
# semana do Postgres começa na segunda (ISO 8601).
_AGRUPAMENTO = {
    Periodo.TRINTA_DIAS: ("dia", "day"),
    Periodo.NOVENTA_DIAS: ("semana", "week"),
    Periodo.DOZE_MESES: ("mes", "month"),
    Periodo.VINTE_E_QUATRO_MESES: ("mes", "month"),
}


@consulta(Perfil.VENDAS)
def evolucao(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Pedidos realizados e receita de cada dia, semana ou mês do período, em ordem.

    Cada ponto começa no primeiro dia do seu dia, semana ou mês de calendário (a segunda da
    semana, o dia 1 do mês), mesmo que o período comece no meio dele; só os pedidos do período
    entram. Pontos sem pedidos aparecem com zero.
    """
    agrupamento, unidade = _AGRUPAMENTO[periodo]
    atual = _datas_do(periodo, conexao)
    linhas = conexao.execute(
        f"""
        with pedidos as (
            select
                date_trunc(%s, {DIA_DO_PEDIDO}::timestamp)::date as ponto,
                g.situacao,
                g.valor
            from vendas.pedido p
            join vendas.pagamento g on g.pedido_id = p.id
            where {NO_PERIODO}
        ),
        pontos as (
            select s::date as inicio
            from generate_series(
                date_trunc(%s, %s::timestamp), %s::timestamp, ('1 ' || %s)::interval
            ) as s
        )
        select
            t.inicio,
            count(d.ponto),
            coalesce(sum(d.valor) filter (where d.situacao = 'Aprovado'), 0)
        from pontos t
        left join pedidos d on d.ponto = t.inicio
        group by t.inicio
        order by t.inicio
        """,
        (unidade, atual.inicio, atual.fim, unidade, atual.inicio, atual.fim, unidade),
    ).fetchall()
    return {
        "agrupamento": agrupamento,
        "pontos": [
            {"inicio": inicio.isoformat(), "pedidos": pedidos, "receita": float(receita)}
            for inicio, pedidos, receita in linhas
        ],
    }


# As quatro situações de entrega, da entrega em aberto à concluída. A resposta traz sempre as
# quatro, nesta ordem, mesmo as que não têm pedido no período.
SITUACOES_DE_ENTREGA = ("Em trânsito", "Prazo vencido", "Entregue no prazo", "Entregue com atraso")


@consulta(Perfil.VENDAS)
def situacao_das_entregas(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Quantos pedidos do período estão em cada situação de entrega.

    Pedido com pagamento recusado não tem entrega e não entra em nenhuma situação.
    """
    datas = _datas_do(periodo, conexao)
    contagens = dict(
        conexao.execute(
            f"""
            select e.situacao, count(*)
            from vendas.pedido p
            join vendas.entrega e on e.pedido_id = p.id
            where {NO_PERIODO}
            group by e.situacao
            """,
            (datas.inicio, datas.fim),
        ).fetchall()
    )
    return {
        "periodo": datas.como_json(),
        "situacoes": [
            {"situacao": situacao, "pedidos": contagens.get(situacao, 0)}
            for situacao in SITUACOES_DE_ENTREGA
        ],
    }


@consulta(Perfil.VENDAS)
def pedidos_recentes(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Os pedidos mais recentes do período, do mais novo para o mais antigo.

    Do cliente, só a cidade e a UF: nenhum identificador sai da consulta. A situação da entrega é
    `None` quando o pagamento foi recusado e não há entrega.
    """
    datas = _datas_do(periodo, conexao)
    linhas = conexao.execute(
        f"""
        select
            p.id, p.momento_compra, p.cliente_cidade, p.cliente_uf, p.lojista_nome, p.rota,
            g.valor, g.situacao, e.situacao
        from vendas.pedido p
        join vendas.pagamento g on g.pedido_id = p.id
        left join vendas.entrega e on e.pedido_id = p.id
        where {NO_PERIODO}
        order by p.momento_compra desc, p.id desc
        limit %s
        """,
        (datas.inicio, datas.fim, LIMITE_DE_PEDIDOS_RECENTES),
    ).fetchall()
    return {
        "periodo": datas.como_json(),
        "pedidos": [
            {
                "numero": numero,
                # Um instante com fuso: o frontend o mostra no horário de Brasília.
                "momento_compra": momento.isoformat(),
                "cidade": cidade,
                "uf": uf,
                "lojista": lojista,
                "rota": rota,
                "valor": float(valor),
                "pagamento": pagamento,
                "entrega": entrega,
            }
            for numero, momento, cidade, uf, lojista, rota, valor, pagamento, entrega in linhas
        ],
    }
