-- Camada de leitura do Comercial (ADR 0002): views comuns, que leem os dados de origem com o
-- direito do dono. O papel comercial só tem uso e leitura neste esquema.

create schema comercial;

-- O lead sem o e-mail de contato e sem o lojista em que ele se tornou: "virou lojista" já está na
-- etapa Fechado, e o nome do lojista é o da empresa do lead. Nada aqui liga um canal aos pedidos,
-- às entregas ou aos atrasos dos lojistas dele: esse padrão só aparece na Diretoria.
create view comercial.lead as
select
    id,
    nome_empresa as empresa,
    canal,
    etapa,
    data_criacao,
    data_fechamento
from dados_de_origem.lead;

-- O último dia coberto pelos dados: as consultas do Comercial calculam o período a partir dele.
create view comercial.referencia as
select data_referencia
from dados_de_origem.referencia;

grant usage on schema comercial to comercial;
grant select on all tables in schema comercial to comercial;
