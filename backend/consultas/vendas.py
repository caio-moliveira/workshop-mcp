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
