-- Camada de leitura de Produtos (ADR 0002): views comuns, que leem os dados de origem com o
-- direito do dono. O papel produtos só tem uso e leitura neste esquema.

create schema produtos;

-- O catálogo inteiro: não há produto ativo ou inativo. O lojista que vende o produto pertence a
-- outros perfis.
create view produtos.produto as
select
    pr.id,
    pr.nome,
    ca.nome as categoria,
    pr.preco
from dados_de_origem.produto pr
join dados_de_origem.categoria ca on ca.id = pr.categoria_id;

-- A avaliação sem o pedido que a originou: cliente, entrega e atraso ficam fora, e o padrão em
-- que o atraso derruba a nota só aparece na Diretoria. O comentário é texto escrito por clientes,
-- não confiável (ADR 0010).
create view produtos.avaliacao as
select
    id,
    produto_id,
    nota,
    comentario,
    data_avaliacao
from dados_de_origem.avaliacao;

-- O último dia coberto pelos dados: as consultas de Produtos calculam o período a partir dele.
create view produtos.referencia as
select data_referencia
from dados_de_origem.referencia;

grant usage on schema produtos to produtos;
grant select on all tables in schema produtos to produtos;
