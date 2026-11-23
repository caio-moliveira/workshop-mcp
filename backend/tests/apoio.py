"""Auxiliares dos testes: o banco carregado e os comandos do desenvolvedor."""

import os
import subprocess
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
RAIZ_DO_PROJETO = BACKEND.parent
PORTA_PADRAO = "5433"

load_dotenv(BACKEND / ".env")


def _variavel(nome: str) -> str:
    valor = os.environ.get(nome)
    if not valor:
        pytest.exit(
            f"Variável {nome} ausente: copie backend/.env.example para backend/.env.",
            returncode=2,
        )
    return valor


def conectar_como_dono() -> psycopg.Connection:
    """Abre uma conexão com o banco carregado usando o papel dono."""
    return psycopg.connect(
        host="127.0.0.1",
        port=int(os.environ.get("POSTGRES_PORT", PORTA_PADRAO)),
        user=_variavel("POSTGRES_USER"),
        password=_variavel("POSTGRES_PASSWORD"),
        dbname=_variavel("BANCO"),
        connect_timeout=5,
        autocommit=True,
    )


def compose(*argumentos: str) -> subprocess.CompletedProcess[str]:
    """Executa um comando do Docker Compose na raiz do projeto."""
    return subprocess.run(
        ["docker", "compose", *argumentos],
        cwd=RAIZ_DO_PROJETO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
