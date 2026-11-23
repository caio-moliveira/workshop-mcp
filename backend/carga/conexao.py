"""Conexão da carga com o Postgres, configurada pelo ambiente do contêiner."""

import os

import psycopg


def variavel(nome: str) -> str:
    """Uma variável de ambiente obrigatória."""
    valor = os.environ.get(nome)
    if not valor:
        raise SystemExit(f"carga: variável de ambiente {nome} ausente")
    return valor


def conectar(banco: str, *, autocommit: bool = False) -> psycopg.Connection:
    """Conecta com o papel dono, o único que a carga usa."""
    return psycopg.connect(
        host=variavel("POSTGRES_HOST"),
        port=int(os.environ.get("POSTGRES_INTERNAL_PORT", "5432")),
        user=variavel("POSTGRES_USER"),
        password=variavel("POSTGRES_PASSWORD"),
        dbname=banco,
        connect_timeout=10,
        autocommit=autocommit,
    )
