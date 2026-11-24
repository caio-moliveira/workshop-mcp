"""O banco da auditoria: a carga cria só o que ainda não existe e nunca o derruba (ADR 0008).

A recarga apaga o banco carregado inteiro (ADR 0001); a auditoria precisa sobreviver a ela.
Uma mudança na estrutura da tabela só chega a um ambiente já criado com `docker compose down`.
"""

import psycopg
from psycopg import sql

from auditoria import BANCO, PAPEL, Resultado
from carga.conexao import conectar, variavel_obrigatoria

VARIAVEL_DA_SENHA = "SENHA_DO_PAPEL_AUDITORIA"

# Uma linha por chamada, com o desfecho final. O horário tem fuso, para ordenar sem ambiguidade.
# Os desfechos aceitos são os do servidor MCP: um desfecho novo entra só em `Resultado`.
ESTRUTURA = sql.SQL("""
create schema if not exists auditoria;

create table if not exists auditoria.chamada (
    id bigint generated always as identity primary key,
    horario timestamptz not null,
    id_do_usuario text not null,
    nome_do_usuario text not null,
    perfil text not null,
    ferramenta text not null,
    parametros jsonb not null,
    parametros_cortados boolean not null,
    resultado text not null check (resultado in ({resultados}))
);
""").format(resultados=sql.SQL(", ").join(sql.Literal(r.value) for r in Resultado))


def preparar_auditoria(conexao: psycopg.Connection) -> None:
    """Cria o banco, o papel e a tabela da auditoria, se faltarem, e reaplica a senha do papel.

    `conexao` é do papel dono, em autocommit, fora do banco da auditoria.
    """
    if not conexao.execute("select 1 from pg_database where datname = %s", (BANCO,)).fetchone():
        print(f"carga: criando o banco {BANCO}")
        conexao.execute(sql.SQL("create database {}").format(sql.Identifier(BANCO)))
    _preparar_papel(conexao)
    with conectar(BANCO, autocommit=True) as no_banco:
        no_banco.execute(ESTRUTURA)
        # Só inserir: o papel não lê, não altera e não apaga (RF-32). A gravação não usa
        # `returning`, que exigiria `select`.
        no_banco.execute(
            sql.SQL("grant usage on schema auditoria to {}").format(sql.Identifier(PAPEL))
        )
        no_banco.execute(
            sql.SQL("grant insert on auditoria.chamada to {}").format(sql.Identifier(PAPEL))
        )


def _preparar_papel(conexao: psycopg.Connection) -> None:
    """Ao contrário dos papéis de perfil, o da auditoria nunca é derrubado: só a senha muda."""
    nome = sql.Identifier(PAPEL)
    if not conexao.execute("select 1 from pg_roles where rolname = %s", (PAPEL,)).fetchone():
        conexao.execute(sql.SQL("create role {} login").format(nome))
    conexao.execute(
        sql.SQL("alter role {} password {}").format(
            nome, sql.Literal(variavel_obrigatoria(VARIAVEL_DA_SENHA))
        )
    )
    conexao.execute(
        sql.SQL("grant connect on database {} to {}").format(sql.Identifier(BANCO), nome)
    )
