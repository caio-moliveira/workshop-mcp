-- Avaliações: a nota que o cliente dá a um produto de um pedido que recebeu.

create table dados_de_origem.avaliacao (
    id integer primary key,
    pedido_id integer not null unique references dados_de_origem.entrega (pedido_id),
    produto_id integer not null references dados_de_origem.produto (id),
    nota smallint not null check (nota between 1 and 5),
    comentario text,
    data_avaliacao date not null,
    -- O produto avaliado é um item do pedido.
    foreign key (pedido_id, produto_id)
        references dados_de_origem.item_pedido (pedido_id, produto_id)
);

create index on dados_de_origem.avaliacao (produto_id);
