"""Grava linhas geradas nos dados de origem, com COPY."""

from dataclasses import astuple, fields
from typing import Any

import psycopg
from psycopg import sql

ESQUEMA = "dados_de_origem"


def gravar(conexao: psycopg.Connection, tabela: str, linhas: list[Any]) -> None:
    """Grava instâncias de um dataclass cujos campos têm os nomes das colunas."""
    if not linhas:
        return
    colunas = [campo.name for campo in fields(linhas[0])]
    comando = sql.SQL("copy {} ({}) from stdin").format(
        sql.Identifier(ESQUEMA, tabela), sql.SQL(", ").join(map(sql.Identifier, colunas))
    )
    with conexao.cursor().copy(comando) as copia:
        for linha in linhas:
            copia.write_row(astuple(linha))
