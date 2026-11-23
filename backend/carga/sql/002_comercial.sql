-- Lado comercial: lojistas e os leads de onde eles vieram.

create table dados_de_origem.lojista (
    id integer primary key,
    nome text not null,
    cnpj char(14) not null unique,
    cidade text not null,
    uf char(2) not null
);

create table dados_de_origem.lead (
    id integer primary key,
    nome_empresa text not null,
    email_contato text not null,
    canal text not null
        check (canal in ('Indicação', 'Orgânico', 'Mídia paga', 'Eventos', 'Prospecção ativa')),
    etapa text not null
        check (etapa in ('Novo', 'Contatado', 'Qualificado', 'Proposta', 'Fechado', 'Perdido')),
    data_criacao date not null,
    data_fechamento date,
    lojista_id integer unique references dados_de_origem.lojista (id),
    check ((etapa = 'Fechado') = (data_fechamento is not null)),
    check ((etapa = 'Fechado') = (lojista_id is not null)),
    check (data_fechamento >= data_criacao)
);
