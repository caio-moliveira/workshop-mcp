"""Os bancos que a recarga não toca (auditoria e histórico): criados só se faltarem, nunca
derrubados (ADR 0008, ADR 0009). Uma mudança na estrutura só chega a um ambiente já criado com
`docker compose down`.
"""

import psycopg
from psycopg import sql

from carga.conexao import variavel_obrigatoria


def criar_banco_se_faltar(conexao: psycopg.Connection, banco: str) -> None:
    """`conexao` é do papel dono, em autocommit, fora do banco."""
    if not conexao.execute("select 1 from pg_database where datname = %s", (banco,)).fetchone():
        print(f"carga: criando o banco {banco}")
        conexao.execute(sql.SQL("create database {}").format(sql.Identifier(banco)))


def preparar_papel(
    conexao: psycopg.Connection, papel: str, variavel_da_senha: str, banco: str
) -> None:
    """Ao contrário dos papéis de perfil, o papel de um banco permanente nunca é derrubado: só a
    senha muda, reaplicada a cada carga. Ele só se conecta ao próprio banco."""
    nome = sql.Identifier(papel)
    if not conexao.execute("select 1 from pg_roles where rolname = %s", (papel,)).fetchone():
        conexao.execute(sql.SQL("create role {} login").format(nome))
    conexao.execute(
        sql.SQL("alter role {} password {}").format(
            nome, sql.Literal(variavel_obrigatoria(variavel_da_senha))
        )
    )
    conexao.execute(
        sql.SQL("grant connect on database {} to {}").format(sql.Identifier(banco), nome)
    )
