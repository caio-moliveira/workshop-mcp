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

-- Resumo por canal do lojista ---------------------------------------------------------------------

-- O canal de cada lojista: o do lead que o originou. Todo lojista vem de um lead fechado.
create view base_da_diretoria.canal_do_lojista as
select l.lojista_id as lojista, l.canal
from dados_de_origem.lead l
where l.lojista_id is not null;

-- O resumo por canal do lojista, uma linha por período e canal, sempre com os cinco canais. A
-- contagem são os pedidos dos lojistas do canal no período, com a regra de Vendas: todo pedido,
-- aprovado ou não, pelo dia da compra no horário de Brasília. Desses pedidos vêm a receita (os
-- pagamentos aprovados) e os entregues e atrasos da taxa de atraso (prazo vencido e em trânsito
-- não entram). A satisfação é a nota média das avaliações feitas no período sobre pedidos dos
-- lojistas do canal, pela data da avaliação, como em Produtos. Na taxa de recompra, o cliente com
-- pedido aprovado no período conta no canal do lojista do primeiro pedido aprovado dele, qualquer
-- que seja a data desse pedido: cada cliente conta num canal só.
create view diretoria.resumo as
with canal (canal) as (
    values ('Indicação'), ('Orgânico'), ('Mídia paga'), ('Eventos'), ('Prospecção ativa')
),
pedidos as (
    select
        pe.periodo,
        c.canal,
        count(*) as pedidos,
        coalesce(sum(g.valor) filter (where g.situacao = 'Aprovado'), 0) as receita,
        count(*) filter (where e.situacao in ('Entregue no prazo', 'Entregue com atraso'))
            as entregues,
        count(*) filter (where e.situacao = 'Entregue com atraso') as atrasos
    from base_da_diretoria.periodo pe
    join dados_de_origem.pedido p
        on (p.momento_compra at time zone 'America/Sao_Paulo')::date between pe.inicio and pe.fim
    join dados_de_origem.pagamento g on g.pedido_id = p.id
    left join dados_de_origem.entrega e on e.pedido_id = p.id
    join base_da_diretoria.canal_do_lojista c on c.lojista = p.lojista_id
    group by pe.periodo, c.canal
),
avaliacoes as (
    select pe.periodo, c.canal, count(*) as avaliacoes, avg(v.nota)::float as satisfacao
    from base_da_diretoria.periodo pe
    join dados_de_origem.avaliacao v on v.data_avaliacao between pe.inicio and pe.fim
    join dados_de_origem.pedido p on p.id = v.pedido_id
    join base_da_diretoria.canal_do_lojista c on c.lojista = p.lojista_id
    group by pe.periodo, c.canal
),
canal_do_cliente as (
    select a.cliente, c.canal
    from base_da_diretoria.pedido_aprovado a
    join base_da_diretoria.canal_do_lojista c on c.lojista = a.lojista
    where not a.recompra
),
clientes as (
    select
        pe.periodo,
        k.canal,
        count(distinct a.cliente) as clientes,
        count(distinct a.cliente) filter (where a.recompra) as clientes_com_recompra
    from base_da_diretoria.periodo pe
    join base_da_diretoria.pedido_aprovado a on a.dia between pe.inicio and pe.fim
    join canal_do_cliente k on k.cliente = a.cliente
    group by pe.periodo, k.canal
)
select
    pe.periodo,
    c.canal,
    coalesce(d.pedidos, 0) as contagem,
    coalesce(d.receita, 0) as receita,
    coalesce(d.entregues, 0) as entregues,
    coalesce(d.atrasos, 0) as atrasos,
    coalesce(v.avaliacoes, 0) as avaliacoes,
    v.satisfacao,
    coalesce(k.clientes, 0) as clientes,
    coalesce(k.clientes_com_recompra, 0) as clientes_com_recompra
from base_da_diretoria.periodo pe
cross join canal c
left join pedidos d on d.periodo = pe.periodo and d.canal = c.canal
left join avaliacoes v on v.periodo = pe.periodo and v.canal = c.canal
left join clientes k on k.periodo = pe.periodo and k.canal = c.canal;

grant select on diretoria.resumo to diretoria;

-- A tendência (#98): os indicadores de cada dia, semana ou mês do período, na granularidade da
-- evolução de Vendas: dia em 30 dias, semana em 90 dias e mês em 12 e 24 meses. Cada ponto começa
-- no primeiro dia do seu dia, semana (a segunda, ISO 8601) ou mês de calendário, mesmo que o
-- período comece no meio dele, e só os dias do período entram nele.
create view base_da_diretoria.ponto_da_tendencia as
select
    pe.periodo,
    s::date as inicio,
    greatest(s::date, pe.inicio) as primeiro_dia,
    least((s + u.passo)::date - 1, pe.fim) as ultimo_dia
from base_da_diretoria.periodo pe
cross join lateral (
    select
        case pe.periodo when '30d' then 'day' when '90d' then 'week' else 'month' end,
        case pe.periodo when '30d' then interval '1 day' when '90d' then interval '1 week'
            else interval '1 month' end
) u (unidade, passo)
cross join lateral generate_series(
    date_trunc(u.unidade, pe.inicio::timestamp), pe.fim::timestamp, u.passo
) s;

-- Uma linha por período e ponto. A contagem é a dos clientes com pedido aprovado no ponto, e a
-- taxa de recompra do ponto é calculada dentro dele: dos clientes do ponto, os que fizeram nele
-- uma recompra. A receita é a de Vendas e a satisfação a de Produtos, com as mesmas regras de
-- data dos indicadores. A taxa de atraso segue a regra de Vendas: dos pedidos do ponto já
-- entregues (no prazo ou com atraso), os entregues com atraso; prazo vencido e em trânsito não
-- entram. A retenção não entra: por dia ela é ruído.
create view diretoria.tendencia as
with pedidos as (
    select
        t.periodo,
        t.inicio,
        count(distinct a.cliente) as contagem,
        count(distinct a.cliente) filter (where a.recompra) as clientes_com_recompra,
        coalesce(sum(a.valor), 0) as receita,
        count(e.pedido_id) filter (
            where e.situacao in ('Entregue no prazo', 'Entregue com atraso')
        ) as entregues,
        count(e.pedido_id) filter (where e.situacao = 'Entregue com atraso') as atrasos
    from base_da_diretoria.ponto_da_tendencia t
    left join base_da_diretoria.pedido_aprovado a
        on a.dia between t.primeiro_dia and t.ultimo_dia
    left join dados_de_origem.entrega e on e.pedido_id = a.pedido
    group by t.periodo, t.inicio
),
avaliacoes as (
    select t.periodo, t.inicio, count(v.nota) as avaliacoes, avg(v.nota)::float as satisfacao
    from base_da_diretoria.ponto_da_tendencia t
    left join dados_de_origem.avaliacao v
        on v.data_avaliacao between t.primeiro_dia and t.ultimo_dia
    group by t.periodo, t.inicio
)
select
    p.periodo,
    p.inicio,
    p.contagem,
    p.clientes_com_recompra,
    p.receita,
    v.avaliacoes,
    v.satisfacao,
    p.entregues,
    p.atrasos
from pedidos p
join avaliacoes v using (periodo, inicio);

grant select on diretoria.tendencia to diretoria;
