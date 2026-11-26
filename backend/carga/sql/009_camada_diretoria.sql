-- Camada de leitura da Diretoria (ADR 0011): views comuns, que leem os dados de origem com o
-- direito do dono, como as outras (ADR 0002), mas já agregadas. Cada view tem uma linha por grupo
-- de uma dimensão fechada, com o período como coluna: traz as linhas dos quatro períodos, e a
-- consulta só filtra o período pedido. Toda view de indicadores traz `contagem`, o tamanho do
-- grupo sobre o qual o número da linha foi calculado. Nenhuma coluna identifica ou localiza um
-- cliente, lojista, lead ou produto, e nenhuma traz comentário.
--
-- As views de apoio ficam no esquema base_da_diretoria, que nenhum papel de perfil lê: só as views
-- da camada as alcançam, pelo direito do dono.

create schema base_da_diretoria;
create schema diretoria;

-- Os quatro períodos, todos terminando na data de referência, e de cada um as datas do período,
-- do anterior de mesmo tamanho e do anterior a esse, com as mesmas regras de consultas/periodo.py:
-- 30 e 90 dias, ou 12 e 24 meses, contando o dia final; no fim de um mês mais curto, o último dia
-- dele. Um período anterior que começaria antes do início dos dados (os 24 meses que terminam na
-- data de referência) fica com as datas nulas: não há com o que comparar.
create view base_da_diretoria.periodo as
with tamanho (periodo, dias, meses) as (
    values ('30d', 30, null), ('90d', 90, null), ('12m', null, 12), ('24m', null, 24)
),
datas as (
    select
        t.periodo,
        (r.data_referencia - interval '24 months')::date + 1 as inicio_dos_dados,
        r.data_referencia as fim,
        a.inicio,
        b.inicio as inicio_anterior,
        c.inicio as inicio_de_dois_periodos_antes
    from dados_de_origem.referencia r
    cross join tamanho t
    -- O início do período que termina em `fim`: a mesma conta três vezes, cada uma terminando na
    -- véspera do início da anterior.
    cross join lateral (
        select case
            when t.dias is not null then r.data_referencia - (t.dias - 1)
            else (r.data_referencia - make_interval(months => t.meses))::date + 1
        end
    ) a (inicio)
    cross join lateral (
        select case
            when t.dias is not null then (a.inicio - 1) - (t.dias - 1)
            else ((a.inicio - 1) - make_interval(months => t.meses))::date + 1
        end
    ) b (inicio)
    cross join lateral (
        select case
            when t.dias is not null then (b.inicio - 1) - (t.dias - 1)
            else ((b.inicio - 1) - make_interval(months => t.meses))::date + 1
        end
    ) c (inicio)
)
select
    periodo,
    inicio,
    fim,
    case when inicio_anterior >= inicio_dos_dados then inicio_anterior end as inicio_anterior,
    case when inicio_anterior >= inicio_dos_dados then inicio - 1 end as fim_anterior,
    case when inicio_de_dois_periodos_antes >= inicio_dos_dados
        then inicio_de_dois_periodos_antes end as inicio_de_dois_periodos_antes,
    case when inicio_de_dois_periodos_antes >= inicio_dos_dados
        then inicio_anterior - 1 end as fim_de_dois_periodos_antes
from datas;

-- Os pedidos com pagamento aprovado, cada um no dia da compra no horário de Brasília, como em
-- Vendas, com o valor aprovado e se ele é uma recompra: um pedido aprovado do cliente que não é o
-- primeiro (glossário). O primeiro é o de compra mais antiga; o identificador desempata.
create view base_da_diretoria.pedido_aprovado as
select
    p.id as pedido,
    p.cliente_id as cliente,
    p.lojista_id as lojista,
    (p.momento_compra at time zone 'America/Sao_Paulo')::date as dia,
    g.valor,
    row_number() over (partition by p.cliente_id order by p.momento_compra, p.id) > 1
        as recompra
from dados_de_origem.pedido p
join dados_de_origem.pagamento g on g.pedido_id = p.id
where g.situacao = 'Aprovado';

-- Os números de um intervalo de dias, para os indicadores: os clientes com pedido aprovado, os que
-- fizeram uma recompra nele, a receita (a soma dos pagamentos aprovados, como em Vendas) e as
-- avaliações com a nota média, pela data da avaliação, como em Produtos.
create view base_da_diretoria.indicadores as
select
    pe.periodo,
    janela.qual,
    (select count(distinct a.cliente) from base_da_diretoria.pedido_aprovado a
      where a.dia between janela.inicio and janela.fim) as clientes,
    (select count(distinct a.cliente) from base_da_diretoria.pedido_aprovado a
      where a.dia between janela.inicio and janela.fim and a.recompra) as clientes_com_recompra,
    (select coalesce(sum(a.valor), 0) from base_da_diretoria.pedido_aprovado a
      where a.dia between janela.inicio and janela.fim) as receita,
    (select count(*) from dados_de_origem.avaliacao v
      where v.data_avaliacao between janela.inicio and janela.fim) as avaliacoes,
    (select avg(v.nota)::float from dados_de_origem.avaliacao v
      where v.data_avaliacao between janela.inicio and janela.fim) as satisfacao,
    -- A retenção da janela: dos clientes com pedido aprovado na janela anterior, os que tiveram
    -- outro pedido aprovado nesta. Nula quando a janela anterior não existe nos dados.
    case when janela.inicio_antes is not null then (
        select count(distinct antes.cliente)
        from base_da_diretoria.pedido_aprovado antes
        where antes.dia between janela.inicio_antes and janela.fim_antes
          and exists (
              select 1 from base_da_diretoria.pedido_aprovado depois
              where depois.cliente = antes.cliente
                and depois.dia between janela.inicio and janela.fim
          )
    ) end as retidos
from base_da_diretoria.periodo pe
cross join lateral (
    values
        ('atual', pe.inicio, pe.fim, pe.inicio_anterior, pe.fim_anterior),
        ('anterior', pe.inicio_anterior, pe.fim_anterior,
            pe.inicio_de_dois_periodos_antes, pe.fim_de_dois_periodos_antes)
) janela (qual, inicio, fim, inicio_antes, fim_antes)
where janela.inicio is not null;

-- Os indicadores consolidados, uma linha por período: os números do período e os do anterior de
-- mesmo tamanho, que as variações pedem, nulos quando ele não existe nos dados. A contagem é a dos
-- clientes com pedido aprovado no período. A retenção do período usa a contagem do anterior como
-- base; a do anterior, a do período de dois para trás.
create view diretoria.indicadores as
select
    pe.periodo,
    atual.clientes as contagem,
    atual.clientes_com_recompra,
    atual.receita,
    atual.avaliacoes,
    atual.satisfacao,
    atual.retidos,
    anterior.clientes as contagem_anterior,
    anterior.clientes_com_recompra as clientes_com_recompra_anterior,
    anterior.receita as receita_anterior,
    anterior.avaliacoes as avaliacoes_anterior,
    anterior.satisfacao as satisfacao_anterior,
    anterior.retidos as retidos_anterior,
    case when pe.inicio_de_dois_periodos_antes is not null then (
        select count(distinct a.cliente) from base_da_diretoria.pedido_aprovado a
        where a.dia between pe.inicio_de_dois_periodos_antes and pe.fim_de_dois_periodos_antes
    ) end as contagem_de_dois_periodos_antes
from base_da_diretoria.periodo pe
join base_da_diretoria.indicadores atual
    on atual.periodo = pe.periodo and atual.qual = 'atual'
left join base_da_diretoria.indicadores anterior
    on anterior.periodo = pe.periodo and anterior.qual = 'anterior';

-- O último dia coberto pelos dados: as consultas da Diretoria calculam o período a partir dele.
create view diretoria.referencia as
select data_referencia
from dados_de_origem.referencia;

grant usage on schema diretoria to diretoria;
grant select on all tables in schema diretoria to diretoria;

-- Fatores de recompra -------------------------------------------------------------------------

-- O primeiro pedido aprovado de cada cliente, qualquer que seja a data dele, com o desfecho da
-- entrega e a nota que o cliente deu a ele. Sem desfecho, o grupo fica nulo: a entrega em trânsito
-- ou com prazo vencido, e o pedido sem avaliação. Nos dados gerados, quem faz recompra sempre
-- avalia o primeiro pedido, e um grupo "sem avaliação" apareceria com 0% por artefato da carga.
create view base_da_diretoria.primeiro_pedido as
select
    a.cliente,
    case e.situacao
        when 'Entregue no prazo' then 'No prazo'
        when 'Entregue com atraso' then 'Com atraso'
    end as entrega,
    case
        when v.nota <= 2 then '1 ou 2'
        when v.nota = 3 then '3'
        when v.nota >= 4 then '4 ou 5'
    end as nota
from base_da_diretoria.pedido_aprovado a
left join dados_de_origem.entrega e on e.pedido_id = a.pedido
left join dados_de_origem.avaliacao v on v.pedido_id = a.pedido
where not a.recompra;

-- Os clientes com pedido aprovado em cada período e se fizeram uma recompra nele: a base da taxa
-- de recompra do cartão.
create view base_da_diretoria.cliente_do_periodo as
select pe.periodo, a.cliente, bool_or(a.recompra) as fez_recompra
from base_da_diretoria.periodo pe
join base_da_diretoria.pedido_aprovado a on a.dia between pe.inicio and pe.fim
group by pe.periodo, a.cliente;

-- Os fatores de recompra, uma linha por período, bloco e grupo, com todos os grupos de todos os
-- blocos em todo período. Nos blocos da primeira entrega e da primeira nota, a contagem é a dos
-- clientes do período cujo primeiro pedido caiu no grupo, e `clientes_com_recompra` os que deles
-- fizeram recompra no período. No da faixa de atraso, a contagem é a das avaliações do período
-- (pela data da avaliação, como em Produtos) cujo pedido foi entregue na faixa, e `satisfacao` a
-- nota média delas.
create view diretoria.fatores_de_recompra as
with grupo (bloco, grupo) as (
    values
        ('primeira_entrega', 'No prazo'),
        ('primeira_entrega', 'Com atraso'),
        ('primeira_nota', '1 ou 2'),
        ('primeira_nota', '3'),
        ('primeira_nota', '4 ou 5'),
        ('faixa_de_atraso', 'No prazo'),
        ('faixa_de_atraso', 'Até 7 dias'),
        ('faixa_de_atraso', 'Mais de 7 dias')
),
recompra as (
    select c.periodo, b.bloco, b.grupo, count(*) as clientes,
           count(*) filter (where c.fez_recompra) as clientes_com_recompra
    from base_da_diretoria.cliente_do_periodo c
    join base_da_diretoria.primeiro_pedido p on p.cliente = c.cliente
    cross join lateral (
        values ('primeira_entrega', p.entrega), ('primeira_nota', p.nota)
    ) b (bloco, grupo)
    where b.grupo is not null
    group by c.periodo, b.bloco, b.grupo
),
satisfacao as (
    select pe.periodo, 'faixa_de_atraso' as bloco, f.faixa as grupo, count(*) as avaliacoes,
           avg(v.nota)::float as satisfacao
    from base_da_diretoria.periodo pe
    join dados_de_origem.avaliacao v on v.data_avaliacao between pe.inicio and pe.fim
    join dados_de_origem.entrega e on e.pedido_id = v.pedido_id
    cross join lateral (
        select case
            when e.data_entrega <= e.data_prometida then 'No prazo'
            when e.data_entrega - e.data_prometida <= 7 then 'Até 7 dias'
            else 'Mais de 7 dias'
        end
    ) f (faixa)
    where e.data_entrega is not null
    group by pe.periodo, f.faixa
)
select
    pe.periodo,
    g.bloco,
    g.grupo,
    coalesce(r.clientes, s.avaliacoes, 0) as contagem,
    case when g.bloco <> 'faixa_de_atraso' then coalesce(r.clientes_com_recompra, 0)
        end as clientes_com_recompra,
    s.satisfacao
from base_da_diretoria.periodo pe
cross join grupo g
left join recompra r on r.periodo = pe.periodo and r.bloco = g.bloco and r.grupo = g.grupo
left join satisfacao s on s.periodo = pe.periodo and s.bloco = g.bloco and s.grupo = g.grupo;

grant select on diretoria.fatores_de_recompra to diretoria;
