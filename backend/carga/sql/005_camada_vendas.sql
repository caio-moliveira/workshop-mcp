-- Camada de leitura de Vendas (ADR 0002): views comuns, que leem os dados de origem com o
-- direito do dono. O papel vendas só tem uso e leitura neste esquema.

create schema vendas;

-- O cliente aparece só pelo identificador, cidade e estado: sem nome, e-mail, documento
-- ou endereço. Notas de avaliação e o canal do lojista pertencem a outros perfis.
create view vendas.pedido as
select
    p.id,
    p.momento_compra,
    p.cliente_id,
    c.cidade as cliente_cidade,
    c.uf as cliente_uf,
    p.lojista_id,
    l.nome as lojista_nome,
    l.uf as lojista_uf,
    l.uf || ' → ' || c.uf as rota,
    p.valor_frete
from dados_de_origem.pedido p
join dados_de_origem.cliente c on c.id = p.cliente_id
join dados_de_origem.lojista l on l.id = p.lojista_id;

create view vendas.item_pedido as
select
    i.pedido_id,
    i.numero,
    i.produto_id,
    pr.nome as produto_nome,
    ca.nome as categoria,
    i.quantidade,
    i.preco_unitario
from dados_de_origem.item_pedido i
join dados_de_origem.produto pr on pr.id = i.produto_id
join dados_de_origem.categoria ca on ca.id = pr.categoria_id;

create view vendas.pagamento as
select pedido_id, forma, parcelas, valor, situacao
from dados_de_origem.pagamento;

create view vendas.entrega as
select pedido_id, data_prometida, data_entrega, situacao
from dados_de_origem.entrega;

grant usage on schema vendas to vendas;
grant select on all tables in schema vendas to vendas;
