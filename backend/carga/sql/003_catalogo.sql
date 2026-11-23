-- Catálogo: categorias e produtos, cada produto vendido por um lojista.

create table dados_de_origem.categoria (
    id integer primary key,
    nome text not null unique
);

create table dados_de_origem.produto (
    id integer primary key,
    nome text not null,
    categoria_id integer not null references dados_de_origem.categoria (id),
    lojista_id integer not null references dados_de_origem.lojista (id),
    preco numeric(12, 2) not null check (preco > 0)
);
