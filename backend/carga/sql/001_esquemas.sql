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

-- A data de referência com que a carga gerou os dados, numa tabela de uma linha. Quem consulta
-- lê o período daqui, nunca de uma configuração própria: dados e consultas não divergem.
create table dados_de_origem.referencia (
    unica boolean primary key default true check (unica),
    data_referencia date not null
);
