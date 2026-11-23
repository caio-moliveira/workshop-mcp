-- Dados de origem: os dados brutos, que nenhum perfil lê diretamente (ADR 0002).
create schema dados_de_origem;

-- Nada de privilégios padrão para PUBLIC: cada papel recebe só o que precisa.
revoke all on schema public from public;

-- Objetos grandes são escrita no banco: ninguém os cria sem permissão explícita.
revoke execute on function
    pg_catalog.lo_create(oid),
    pg_catalog.lo_creat(integer),
    pg_catalog.lo_from_bytea(oid, bytea)
from public;
