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
from consultas.periodo import Intervalo, Periodo, terminado_em
from consultas.registro import consulta

# O dia de um pedido, no fuso do negócio, venha a sessão com o fuso que vier.
DIA_DO_PEDIDO = "(p.momento_compra at time zone 'America/Sao_Paulo')::date"

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


def _inicio_dos_dados(conexao: psycopg.Connection) -> date | None:
    return conexao.execute(f"select min({DIA_DO_PEDIDO}) from vendas.pedido p").fetchone()[0]


def _resumo(conexao: psycopg.Connection, intervalo: Intervalo) -> _Resumo:
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
        where {DIA_DO_PEDIDO} between %s and %s
        """,
        (intervalo.inicio, intervalo.fim),
    ).fetchone()
    return _Resumo(*linha)


@consulta(Perfil.VENDAS)
def indicadores(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Pedidos realizados, receita, taxa de atraso e taxa de aprovação do período e do anterior.

    O anterior tem o mesmo tamanho e termina na véspera do início. É `None` quando começaria
    antes do início dos dados, onde não haveria com o que comparar.
    """
    atual = terminado_em(periodo, _data_de_referencia(conexao))
    intervalo_anterior = atual.anterior(periodo)
    inicio_dos_dados = _inicio_dos_dados(conexao)
    agora = _resumo(conexao, atual)
    antes = (
        _resumo(conexao, intervalo_anterior)
        if inicio_dos_dados and intervalo_anterior.inicio >= inicio_dos_dados
        else None
    )

    def par(indicador: Callable[[_Resumo], object]) -> dict:
        return {"atual": indicador(agora), "anterior": None if antes is None else indicador(antes)}

    return {
        "periodo": {"inicio": atual.inicio.isoformat(), "fim": atual.fim.isoformat()},
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

    Cada ponto começa no início do seu intervalo de calendário (a segunda da semana, o dia 1 do
    mês), mesmo que o período comece no meio dele; só os pedidos do período entram. Intervalos sem
    pedidos aparecem com zero.
    """
    agrupamento, unidade = _AGRUPAMENTO[periodo]
    atual = terminado_em(periodo, _data_de_referencia(conexao))
    linhas = conexao.execute(
        f"""
        with pedidos as (
            select
                date_trunc(%(unidade)s, {DIA_DO_PEDIDO}::timestamp)::date as intervalo,
                g.situacao,
                g.valor
            from vendas.pedido p
            join vendas.pagamento g on g.pedido_id = p.id
            where {DIA_DO_PEDIDO} between %(inicio)s and %(fim)s
        ),
        intervalos as (
            select i::date as inicio
            from generate_series(
                date_trunc(%(unidade)s, %(inicio)s::timestamp),
                %(fim)s::timestamp,
                ('1 ' || %(unidade)s)::interval
            ) as i
        )
        select
            i.inicio,
            count(d.intervalo),
            coalesce(sum(d.valor) filter (where d.situacao = 'Aprovado'), 0)
        from intervalos i
        left join pedidos d on d.intervalo = i.inicio
        group by i.inicio
        order by i.inicio
        """,
        {"unidade": unidade, "inicio": atual.inicio, "fim": atual.fim},
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
    intervalo = terminado_em(periodo, _data_de_referencia(conexao))
    contagens = dict(
        conexao.execute(
            f"""
            select e.situacao, count(*)
            from vendas.pedido p
            join vendas.entrega e on e.pedido_id = p.id
            where {DIA_DO_PEDIDO} between %s and %s
            group by e.situacao
            """,
            (intervalo.inicio, intervalo.fim),
        ).fetchall()
    )
    return {
        "periodo": {"inicio": intervalo.inicio.isoformat(), "fim": intervalo.fim.isoformat()},
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
    intervalo = terminado_em(periodo, _data_de_referencia(conexao))
    linhas = conexao.execute(
        f"""
        select
            p.id, p.momento_compra, p.cliente_cidade, p.cliente_uf, p.lojista_nome, p.rota,
            g.valor, g.situacao, e.situacao
        from vendas.pedido p
        join vendas.pagamento g on g.pedido_id = p.id
        left join vendas.entrega e on e.pedido_id = p.id
        where {DIA_DO_PEDIDO} between %s and %s
        order by p.momento_compra desc, p.id desc
        limit %s
        """,
        (intervalo.inicio, intervalo.fim, LIMITE_DE_PEDIDOS_RECENTES),
    ).fetchall()
    return {
        "periodo": {"inicio": intervalo.inicio.isoformat(), "fim": intervalo.fim.isoformat()},
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
