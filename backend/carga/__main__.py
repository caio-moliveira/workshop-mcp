"""Executa a carga: derruba o banco, recria e aplica a estrutura em ordem.

A recarga é esta mesma execução, para que "subir do zero" e "voltar ao
estado inicial" nunca divirjam (ADR 0001).
"""

import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

DIRETORIO_SQL = Path(__file__).resolve().parent / "sql"


def _variavel(nome: str) -> str:
    valor = os.environ.get(nome)
    if not valor:
        raise SystemExit(f"carga: variável de ambiente {nome} ausente")
    return valor


def _conectar(banco: str, *, autocommit: bool = False) -> psycopg.Connection:
    return psycopg.connect(
        host=_variavel("POSTGRES_HOST"),
        port=int(os.environ.get("POSTGRES_INTERNAL_PORT", "5432")),
        user=_variavel("POSTGRES_USER"),
        password=_variavel("POSTGRES_PASSWORD"),
        dbname=banco,
        connect_timeout=10,
        autocommit=autocommit,
    )


def _recriar_banco(banco: str) -> None:
    with _conectar("postgres", autocommit=True) as conexao:
        nome = sql.Identifier(banco)
        conexao.execute(sql.SQL("drop database if exists {} with (force)").format(nome))
        conexao.execute(sql.SQL("create database {}").format(nome))


def _aplicar_estrutura(banco: str) -> None:
    with _conectar(banco) as conexao:
        for arquivo in sorted(DIRETORIO_SQL.glob("*.sql")):
            print(f"carga: aplicando {arquivo.name}")
            conexao.execute(arquivo.read_text(encoding="utf-8"))


def main() -> int:
    banco = _variavel("BANCO")
    try:
        print(f"carga: recriando o banco {banco}")
        _recriar_banco(banco)
        _aplicar_estrutura(banco)
    except psycopg.Error as erro:
        print(f"carga: falhou: {erro}", file=sys.stderr)
        return 1
    print("carga: concluída")
    return 0


if __name__ == "__main__":
    sys.exit(main())
