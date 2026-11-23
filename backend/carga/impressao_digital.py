"""Impressão digital lógica do banco: um hash por tabela dos dados de origem.

Duas cargas são "o mesmo banco" quando as impressões digitais coincidem. O hash cobre o
conteúdo das linhas, ordenadas pela chave primária, e não detalhes físicos do Postgres.
"""

import psycopg
from psycopg import sql

from carga.gravacao import ESQUEMA

_TABELAS_E_CHAVES = """
select c.relname, array_agg(a.attname order by k.posicao) filter (where a.attname is not null)
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
left join pg_index i on i.indrelid = c.oid and i.indisprimary
left join lateral unnest(i.indkey::int2[]) with ordinality as k (coluna, posicao) on true
left join pg_attribute a on a.attrelid = c.oid and a.attnum = k.coluna
where n.nspname = %s and c.relkind = 'r'
group by c.relname
order by c.relname
"""


def impressao_digital(conexao: psycopg.Connection) -> dict[str, str]:
    """Devolve, para cada tabela dos dados de origem, o MD5 das suas linhas em ordem de chave."""
    impressao: dict[str, str] = {}
    for tabela, chave in conexao.execute(_TABELAS_E_CHAVES, (ESQUEMA,)).fetchall():
        if not chave:
            raise ValueError(f"a tabela {tabela} não tem chave primária")
        consulta = sql.SQL(
            "select md5(coalesce(string_agg(t::text, E'\n' order by {}), '')) from {} t"
        ).format(
            sql.SQL(", ").join(sql.Identifier("t", coluna) for coluna in chave),
            sql.Identifier(ESQUEMA, tabela),
        )
        impressao[tabela] = conexao.execute(consulta).fetchone()[0]
    return impressao
