"""Auxiliares dos testes: o banco carregado e os comandos do desenvolvedor."""

import os
import subprocess
from datetime import date
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


PREFIXO_DA_IMPRESSAO_DIGITAL = "carga: impressão digital "


def rodar_carga(*variaveis: str) -> dict[str, str]:
    """Roda a carga pelo comando do desenvolvedor e devolve a impressão digital por tabela.

    Cada variável vem no formato NOME=valor e sobrepõe a configuração só nesta execução.
    """
    opcoes = [opcao for variavel in variaveis for opcao in ("-e", variavel)]
    resultado = compose("run", "--rm", *opcoes, "carga")
    assert resultado.returncode == 0, resultado.stderr
    impressao: dict[str, str] = {}
    for linha in resultado.stdout.splitlines():
        if linha.startswith(PREFIXO_DA_IMPRESSAO_DIGITAL):
            tabela, valor = linha.removeprefix(PREFIXO_DA_IMPRESSAO_DIGITAL).split()
            impressao[tabela] = valor
    return impressao


def contar(conexao: psycopg.Connection, tabela: str) -> int:
    """Quantidade de linhas de uma tabela dos dados de origem."""
    return conexao.execute(f"select count(*) from dados_de_origem.{tabela}").fetchone()[0]


def tabelas_dos_dados_de_origem(conexao: psycopg.Connection) -> set[str]:
    """Nomes de todas as tabelas dos dados de origem."""
    return {
        linha[0]
        for linha in conexao.execute(
            "select table_name from information_schema.tables"
            " where table_schema = 'dados_de_origem'"
        )
    }


# Datas que são compromissos, e não eventos: podem estar depois da data de referência.
# A entrega prometida de um pedido em trânsito ainda não chegou.
COLUNAS_DE_COMPROMISSO = ("data_prometida",)


def intervalo_de_datas(conexao: psycopg.Connection) -> tuple[date, date]:
    """A menor e a maior data de evento em todas as colunas de data dos dados de origem."""
    colunas = conexao.execute(
        """
        select table_name, column_name from information_schema.columns
        where table_schema = 'dados_de_origem'
            and data_type in ('date', 'timestamp without time zone', 'timestamp with time zone')
            and column_name <> all(%s)
        order by table_name, column_name
        """,
        (list(COLUNAS_DE_COMPROMISSO),),
    ).fetchall()
    assert colunas, "nenhuma coluna de data nos dados de origem"
    partes = [
        f"select min({coluna}::date) as menor, max({coluna}::date) as maior"
        f" from dados_de_origem.{tabela}"
        for tabela, coluna in colunas
    ]
    return conexao.execute(
        f"select min(menor), max(maior) from ({' union all '.join(partes)}) datas"
    ).fetchone()
