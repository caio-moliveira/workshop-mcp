"""As consultas do painel de Vendas. Leem só a camada de leitura de Vendas (ADR 0002)."""

import psycopg

from acesso import Perfil
from consultas.periodo import Periodo, terminado_em
from consultas.registro import consulta


def _data_de_referencia(conexao: psycopg.Connection):
    return conexao.execute("select data_referencia from vendas.referencia").fetchone()[0]


@consulta(Perfil.VENDAS)
def indicadores(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Pedidos realizados, receita, taxa de atraso e taxa de aprovação do período."""
    atual = terminado_em(periodo, _data_de_referencia(conexao))
    return {"periodo": {"inicio": atual.inicio.isoformat(), "fim": atual.fim.isoformat()}}
