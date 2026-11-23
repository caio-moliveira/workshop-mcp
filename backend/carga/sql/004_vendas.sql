-- Operação de vendas: clientes, pedidos, itens, pagamentos e entregas.

create table dados_de_origem.cliente (
    id integer primary key,
    nome text not null,
    email text not null,
    cpf char(11) not null unique,
    endereco text not null,
    cidade text not null,
    uf char(2) not null
);

create table dados_de_origem.pedido (
    id integer primary key,
    cliente_id integer not null references dados_de_origem.cliente (id),
    lojista_id integer not null references dados_de_origem.lojista (id),
    momento_compra timestamptz not null,
    valor_frete numeric(10, 2) not null check (valor_frete >= 0)
);

create index on dados_de_origem.pedido (cliente_id);
create index on dados_de_origem.pedido (lojista_id);
create index on dados_de_origem.pedido (momento_compra);

create table dados_de_origem.item_pedido (
    pedido_id integer not null references dados_de_origem.pedido (id),
    numero smallint not null,
    produto_id integer not null references dados_de_origem.produto (id),
    quantidade smallint not null check (quantidade > 0),
    preco_unitario numeric(12, 2) not null check (preco_unitario > 0),
    primary key (pedido_id, numero)
);

create index on dados_de_origem.item_pedido (produto_id);

-- Um pagamento por pedido.
create table dados_de_origem.pagamento (
    pedido_id integer primary key references dados_de_origem.pedido (id),
    forma text not null check (forma in ('Cartão de crédito', 'Pix', 'Boleto')),
    parcelas smallint not null check (parcelas between 1 and 12),
    valor numeric(12, 2) not null check (valor > 0),
    situacao text not null check (situacao in ('Aprovado', 'Recusado')),
    check (forma = 'Cartão de crédito' or parcelas = 1)
);

-- Só pedidos com pagamento aprovado têm entrega.
create table dados_de_origem.entrega (
    pedido_id integer primary key references dados_de_origem.pedido (id),
    data_prometida date not null,
    data_entrega date,
    situacao text not null check (
        situacao in ('Em trânsito', 'Prazo vencido', 'Entregue no prazo', 'Entregue com atraso')
    ),
    check ((situacao like 'Entregue%') = (data_entrega is not null)),
    check (situacao <> 'Entregue no prazo' or data_entrega <= data_prometida),
    check (situacao <> 'Entregue com atraso' or data_entrega > data_prometida)
);
