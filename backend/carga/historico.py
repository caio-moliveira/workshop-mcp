"""O banco do histórico: a carga cria só o que ainda não existe e nunca o derruba (ADR 0009).

Como a auditoria, o histórico precisa sobreviver à recarga, que apaga o banco carregado inteiro.
"""

import psycopg
from psycopg import sql

from carga.banco_permanente import criar_banco_se_faltar, preparar_papel
from carga.conexao import conectar
from historico import BANCO, PAPEL, Situacao

VARIAVEL_DA_SENHA = "SENHA_DO_PAPEL_HISTORICO"

# A conversa é do usuário (`sub`) com o perfil que tinha ao criá-la: com outro perfil, ele não a
# vê. A ordem dos itens é a de gravação. Só a resposta tem situação; a pergunta nunca tem. O
# rastreio (chamadas da resposta) já nasce aqui, vazio, para não exigir `docker compose down`
# quando passar a ser gravado. Apagar a conversa apaga os itens dela.
ESTRUTURA = sql.SQL("""
create schema if not exists historico;

create table if not exists historico.conversa (
    id uuid primary key,
    id_do_usuario text not null,
    perfil text not null,
    titulo text not null,
    ultima_atividade timestamptz not null
);

create index if not exists conversa_por_atividade
    on historico.conversa (id_do_usuario, perfil, ultima_atividade desc);

create table if not exists historico.item (
    ordem bigint generated always as identity primary key,
    id_da_conversa uuid not null references historico.conversa (id) on delete cascade,
    autor text not null check (autor in ('usuario', 'assistente')),
    texto text not null,
    horario timestamptz not null,
    situacao text check (situacao in ({situacoes})),
    aviso text,
    erro text,
    id_da_pergunta uuid,
    rastreio jsonb not null default '[]',
    check ((autor = 'assistente') = (situacao is not null))
);

create index if not exists item_da_conversa on historico.item (id_da_conversa, ordem);
""").format(situacoes=sql.SQL(", ").join(sql.Literal(s.value) for s in Situacao))


def preparar_historico(conexao: psycopg.Connection) -> None:
    """Cria o banco, o papel e as tabelas do histórico, se faltarem, e reaplica a senha do papel.

    `conexao` é do papel dono, em autocommit, fora do banco do histórico.
    """
    criar_banco_se_faltar(conexao, BANCO)
    preparar_papel(conexao, PAPEL, VARIAVEL_DA_SENHA, BANCO)
    papel = sql.Identifier(PAPEL)
    with conectar(BANCO, autocommit=True) as no_banco:
        no_banco.execute(ESTRUTURA)
        # Lê, grava e apaga conversas; atualiza só a última atividade. Nada de estrutura.
        no_banco.execute(sql.SQL("grant usage on schema historico to {}").format(papel))
        no_banco.execute(
            sql.SQL(
                "grant select, insert, delete, update (ultima_atividade)"
                " on historico.conversa to {}"
            ).format(papel)
        )
        no_banco.execute(
            sql.SQL("grant select, insert, delete on historico.item to {}").format(papel)
        )
