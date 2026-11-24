"""O mecanismo de consultas compartilhado: o único lugar que lê o banco em nome de um usuário.

Cada consulta declara um perfil. O executor confere o perfil do usuário autenticado antes de
qualquer coisa e só então conecta ao banco com o papel daquele perfil (RF-13, RS-04, RS-05). A API
o usa; o servidor MCP vai usá-lo também.
"""

from consultas.executor import (
    AcessoNegado,
    BancoDeDados,
    ConsultaFalhou,
    Credencial,
    ExecutorDeConsultas,
    credenciais_do_ambiente,
)
from consultas.periodo import PERIODO_PADRAO, DatasDoPeriodo, ParametroInvalido, Periodo
from consultas.registro import Consulta, consulta

__all__ = [
    "PERIODO_PADRAO",
    "AcessoNegado",
    "BancoDeDados",
    "Consulta",
    "ConsultaFalhou",
    "Credencial",
    "DatasDoPeriodo",
    "ExecutorDeConsultas",
    "ParametroInvalido",
    "Periodo",
    "consulta",
    "credenciais_do_ambiente",
]
