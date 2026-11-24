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


def variavel(nome: str) -> str:
    """O valor de uma variável de ambiente obrigatória; encerra os testes se faltar."""
    valor = os.environ.get(nome)
    if not valor:
        pytest.exit(
            f"Variável {nome} ausente: copie backend/.env.example para backend/.env.",
            returncode=2,
        )
    return valor


def _conectar(usuario: str, senha: str, banco: str | None) -> psycopg.Connection:
    return psycopg.connect(
        host="127.0.0.1",
        port=int(os.environ.get("POSTGRES_PORT", PORTA_PADRAO)),
        user=usuario,
        password=senha,
        dbname=banco or variavel("BANCO"),
        connect_timeout=5,
        autocommit=True,
    )


def conectar_como_dono(banco: str | None = None) -> psycopg.Connection:
    """Abre uma conexão usando o papel dono (por padrão, no banco carregado)."""
    return _conectar(variavel("POSTGRES_USER"), variavel("POSTGRES_PASSWORD"), banco)


def conectar_como_vendas(banco: str | None = None) -> psycopg.Connection:
    """Abre uma conexão usando a credencial do papel de Vendas (por padrão, no banco carregado)."""
    return _conectar("vendas", variavel("SENHA_DO_PAPEL_VENDAS"), banco)


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
    return _impressao_da_saida(compose("run", "--rm", *opcoes, "carga"))


def impressao_digital_atual() -> dict[str, str]:
    """A impressão digital do banco como ele está agora, sem recarregar."""
    return _impressao_da_saida(
        compose("run", "--rm", "carga", "python", "-m", "carga.impressao_digital")
    )


def _impressao_da_saida(resultado: subprocess.CompletedProcess[str]) -> dict[str, str]:
    assert resultado.returncode == 0, resultado.stderr
    impressao: dict[str, str] = {}
    for linha in resultado.stdout.splitlines():
        if linha.startswith(PREFIXO_DA_IMPRESSAO_DIGITAL):
            tabela, hash_da_tabela = linha.removeprefix(PREFIXO_DA_IMPRESSAO_DIGITAL).split()
            impressao[tabela] = hash_da_tabela
    assert impressao, resultado.stdout
    return impressao


def valor(conexao: psycopg.Connection, consulta: str):
    """O único valor que uma consulta devolve."""
    return conexao.execute(consulta).fetchone()[0]


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
