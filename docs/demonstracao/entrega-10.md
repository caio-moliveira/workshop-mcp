# Roteiro de demonstração: entrega 10, perfil Diretoria

Este roteiro mostra o que a 10 acrescenta: o perfil Diretoria ganha o caminho inteiro que os outros três já têm (camada de leitura com o papel `diretoria`, quatro rotas na API, quatro ferramentas no servidor MCP, painel e pergunta sugerida no assistente), e a matriz de isolamento passa a cruzar os quatro perfis (CA-01, CA-02). A diferença é a forma da camada: ela só tem indicadores consolidados, uma linha por grupo, com o período como coluna (ADR 0011), e é a única que cruza as três áreas. É aqui que a história dos dados fecha: quem teve a primeira entrega com atraso não volta, quem deu nota 1 ou 2 quase não volta, o atraso derruba a nota, e Mídia paga, o canal que mais converte no Comercial, é o canal cujos lojistas mais atrasam. Os comandos rodam na raiz do projeto, salvo quando o passo indica `backend/`. Onde o PowerShell e o bash diferem, vale o que os roteiros da 5b e da 8 mostram.

Pré-requisitos: Docker com Docker Compose, [uv](https://docs.astral.sh/uv/), Node.js 24 (para o MCP Inspector), um navegador e uma chave da API da Anthropic (o provedor do modelo padrão).

**O que foi conferido e como.** Em 26/11/2026, todos os passos foram executados num ambiente subido do zero (`docker compose down -v` e `docker compose up -d --build --wait`, a partir do código da branch de integração da entrega, `feat/96-perfil-diretoria`), com o `mcp` no limite padrão de frequência (30 chamadas por usuário por minuto). Os passos 2 a 5 e o 7 foram executados pela API e pelo servidor MCP, com o modelo real (`anthropic:claude-haiku-5-5`, o padrão): o token de cada usuário veio do mesmo login dos testes (fluxo de código com PKCE), e a pergunta foi enviada em `POST /assistente`, como o painel faz, com o fluxo de eventos lido até o `fim`. O passo 6 foi conferido no Chrome, pelo agente, com os números comparados aos das rotas. As respostas do modelo mudam a cada execução; o que este roteiro anota é o resultado observado e o que deve se repetir. O que não foi conferido está na seção "Lacunas".

## 1. Configurar e subir

```
cp backend/.env.example backend/.env
```

No `backend/.env`, preencha `ANTHROPIC_API_KEY` e troque as senhas. Esta entrega acrescenta uma variável. **Quem já tem um `backend/.env` de antes da 10 precisa acrescentá-la e refazer a carga** (`docker compose run --rm --build carga`), que cria o papel e a camada de leitura da Diretoria:

| Variável | O que é |
| --- | --- |
| `SENHA_DO_PAPEL_DIRETORIA` | A senha do papel `diretoria`, com que a API e o servidor MCP leem a camada de leitura da Diretoria, e só ela (ADR 0002, ADR 0011). Sem ela, o perfil Diretoria é negado em toda consulta |

Suba do zero, com o `mcp` no limite padrão de frequência:

```
docker compose down -v
docker compose up -d --build --wait
```

**Executado em 26/11/2026:** todos os contêineres `healthy` e a carga `Exited (0)`, com `carga: concluída` no log, em 35 s (imagens em cache). O banco `historico` com 0 conversas e a auditoria com 0 linhas; o `mcp` com `LIMITE_DE_CHAMADAS_POR_USUARIO` 30:

```
docker compose exec postgres psql -U dono -d historico -tAc "select count(*) from historico.conversa"
docker compose exec postgres psql -U dono -d auditoria -tAc "select count(*) from auditoria.chamada"
```

### Como perguntar pelo terminal

Como nos roteiros da 5b, da 8 e da 9, emita o token da aplicação dentro de `backend/` (vale 5 minutos):

```
TOKEN=$(uv run python -m token_de_demonstracao diego.diretoria pulso-web)
```

A pergunta, com o fluxo de eventos lido até o `fim`:

```
curl -sN -X POST http://localhost:8000/assistente -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"pergunta":"Por que os clientes compram uma vez e não voltam?"}'
```

As rotas do painel da Diretoria, com o mesmo token. Todas recebem só o período:

```
curl -s "http://localhost:8000/diretoria/indicadores?periodo=12m" -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/diretoria/tendencia?periodo=12m" -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/diretoria/fatores-de-recompra?periodo=12m" -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/diretoria/resumo?periodo=12m" -H "Authorization: Bearer $TOKEN"
```

**Executado em 26/11/2026**, com o token de `diego.diretoria`, nos quatro períodos (todas 200). Os indicadores:

| Período | Receita (anterior) | Taxa de recompra (anterior) | Satisfação (anterior) | Retenção (anterior) |
| --- | ---: | ---: | ---: | ---: |
| 30 dias | R$ 2.405.996,39 (1.347.654,75) | 14,2%, 308 de 2.173 (12,9%) | 4,12 em 1.237 avaliações (4,07) | 0,8%, 11 de 1.296 (0,7%) |
| 90 dias | R$ 5.015.756,51 (3.846.648,49) | 12,5%, 593 de 4.726 (8,2%) | 4,10 em 3.067 (4,10) | 5,4%, 191 de 3.545 (2,1%) |
| 12 meses | R$ 17.082.039,33 (13.543.930,03) | 7,8%, 1.204 de 15.379 (1,4%) | 4,09 em 11.594 (4,09) | 4,6%, 573 de 12.495 (sem anterior) |
| 24 meses | R$ 30.625.969,36 (sem anterior) | 5,0%, 1.365 de 27.301 (sem anterior) | 4,09 em 20.114 (sem anterior) | sem valor (sem anterior) |

As contagens são as de referência da spec (clientes 2.173, 4.726, 15.379 e 27.301; recompra 308, 593, 1.204 e 1.365; retenção 11 de 1.296, 191 de 3.545 e 573 de 12.495). A retenção não existe em 24 meses, e a variação dela não existe em 12 nem em 24 meses. A taxa de recompra sobe nos períodos curtos (5,0% em 24 meses, 14,2% em 30 dias), como o glossário avisa: não é melhora.

**Igualdade entre perfis**, com o token de `ana.vendas` e de `bruno.produtos` no mesmo período: a receita da Diretoria é igual, centavo a centavo, à de `/vendas/indicadores` nos quatro períodos, e a satisfação é igual à nota média de `/produtos/indicadores` nos quatro (4,12287…, 4,09748…, 4,09047… e 4,08819…). No resumo por canal em 12 meses, os pedidos (16.795), a receita (R$ 17.082.039,33) e os atrasos (1.411 de 15.622 entregues, 9,0%) somam os totais de Vendas.

Os fatores de recompra (clientes com recompra de clientes do grupo; satisfação com o número de avaliações):

| Período | 1ª entrega no prazo | 1ª entrega com atraso | 1ª nota 1 ou 2 | 1ª nota 3 | 1ª nota 4 ou 5 | Nota no prazo | Até 7 dias | Mais de 7 dias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 dias | 308 de 1.706 (18,1%) | 0 de 62 | 3 de 71 (4,2%) | 21 de 88 (23,9%) | 284 de 839 (33,8%) | 4,23 (1.161) | 2,80 (40) | 2,00 (36) |
| 90 dias | 593 de 4.051 (14,6%) | 0 de 269 | 4 de 274 (1,5%) | 57 de 263 (21,7%) | 532 de 2.347 (22,7%) | 4,26 (2.808) | 2,85 (123) | 1,80 (136) |
| 12 meses | 1.204 de 13.660 (8,8%) | 0 de 1.313 | 10 de 1.258 (0,8%) | 107 de 1.044 (10,2%) | 1.087 de 8.408 (12,9%) | 4,28 (10.514) | 2,83 (533) | 1,75 (547) |
| 24 meses | 1.365 de 24.310 (5,6%) | 0 de 2.585 | 11 de 2.420 (0,5%) | 120 de 1.898 (6,3%) | 1.234 de 14.870 (8,3%) | 4,28 (18.205) | 2,84 (960) | 1,75 (949) |

Os três elos aparecem nos quatro períodos. Os de 12 meses são os de referência da spec.

O resumo por canal, na ordem em que a rota devolve (da maior taxa de atraso para a menor), em 12 meses:

| Canal | Pedidos | Receita | Taxa de atraso | Satisfação | Taxa de recompra |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mídia paga | 9.214 | R$ 8.836.743,17 | 12,8% (1.094 de 8.569) | 4,02 | 7,9% (663 de 8.443) |
| Prospecção ativa | 1.510 | R$ 2.051.376,60 | 6,4% (89 de 1.384) | 4,15 | 7,2% |
| Orgânico | 3.448 | R$ 4.122.211,99 | 5,0% (161 de 3.212) | 4,16 | 7,7% |
| Eventos | 937 | R$ 780.782,82 | 3,0% (26 de 881) | 4,18 | 8,5% |
| Indicação | 1.686 | R$ 1.290.924,75 | 2,6% (41 de 1.576) | 4,26 | 8,2% |

Mídia paga é o canal que mais atrasa nos quatro períodos: 6,2% em 30 dias, 10,4% em 90 dias, 12,8% em 12 meses e 13,3% em 24 meses (2.131 de 15.974 entregas), contra 0,0% a 5,7% nos outros quatro. A taxa de recompra quase não muda entre os canais (7,2% a 8,5% em 12 meses): o efeito do canal passa pelo atraso.

A tendência: 30 pontos por dia em 30 dias, 14 por semana em 90 dias, 12 e 24 por mês em 12 e 24 meses, cada um com receita, taxa de recompra, satisfação e taxa de atraso, e as contagens ao lado. O último dia (30/11/2026) não tem taxa de atraso: nenhum pedido dele foi entregue ainda.

## 2. A pergunta sugerida da Diretoria

Com o token de `diego.diretoria`, pergunte `Por que os clientes compram uma vez e não voltam?` (a pergunta sugerida do painel).

**O que se espera:** 200; o evento `conversa` primeiro; uma `chamada` a `diretoria_fatores_de_recompra` (e, se o modelo quiser, a `diretoria_resumo`), `concluida`; o `fim`. A resposta cita os três elos (quem teve a primeira entrega com atraso não volta, quem deu nota 1 ou 2 quase não volta, e o atraso derruba a nota) com números que conferem com as rotas, aponta Mídia paga como o canal que mais atrasa e não cita lojista, cliente nem produto.

**Executado pela API (26/11/2026), primeira vez.** 200; o `conversa` primeiro; um `estado` e uma `chamada` (`diretoria_fatores_de_recompra`, `concluida`, 95 ms) 1,6 s depois; 88 trechos de texto e o `fim` 5,8 s depois do `conversa`. A resposta:

> Os dados indicam que **atraso na primeira entrega e nota baixa no primeiro pedido andam junto com a falta de recompra**. Não é possível afirmar que um causa o outro, mas os números são claros.
>
> **Entrega do primeiro pedido**
>
> | Entrega do 1º pedido | Clientes | Taxa de recompra |
> |---|---|---|
> | No prazo | 13.660 | 8,8% |
> | Com atraso | 1.313 | 0% |
>
> Nenhum dos clientes cujo primeiro pedido atrasou voltou a comprar.
>
> **Nota dada ao primeiro pedido**
>
> | Nota | Clientes | Taxa de recompra |
> |---|---|---|
> | 1 ou 2 | 1.258 | 0,8% |
> | 3 | 1.044 | 10,2% |
> | 4 ou 5 | 8.408 | 12,9% |
>
> **Atraso e satisfação**
>
> A nota média cai conforme o atraso aumenta:
> - No prazo: 4,28
> - Até 7 dias de atraso: 2,83
> - Mais de 7 dias de atraso: 1,75
>
> Os clientes que ainda não receberam o primeiro pedido, ou que não o avaliaram, ficam fora desses grupos. Por isso a soma de cada tabela não chega ao total de clientes do período.

**Segunda vez, numa conversa nova.** Uma chamada a `diretoria_fatores_de_recompra` (81 ms), `fim` em 5,0 s. A mesma estrutura, em listas: "Entrega no prazo: 8,8% recompraram (1.204 de 13.660 clientes). Entrega com atraso: 0% recompraram (0 de 1.313 clientes)", as três faixas de nota com as contagens (10 de 1.258, 107 de 1.044, 1.087 de 8.408), as três notas médias com o número de avaliações (10.514, 533 e 547) e o fecho "o atraso aparece junto com a nota baixa, e a nota baixa junto com quase nenhuma recompra". Repetiu a ressalva dos grupos deixados de fora.

**Veredito, nas duas execuções:**

| Ponto do critério | Resultado |
| --- | --- |
| Usa `diretoria_fatores_de_recompra` | Sim, uma chamada, com `periodo` 12m. Não chamou `diretoria_resumo` |
| Primeira entrega com atraso não volta | Sim: 0% de 1.313 contra 8,8% de 13.660, iguais à rota em 12 meses |
| Nota 1 ou 2 quase não volta | Sim: 0,8% de 1.258, contra 10,2% e 12,9%, iguais à rota |
| O atraso derruba a nota | Sim: 4,28, 2,83 e 1,75, iguais à rota (4,276, 2,831 e 1,748) |
| Aponta Mídia paga como o canal que mais atrasa | **Não.** Nenhuma das duas respostas fala de canal, porque o modelo não chamou `diretoria_resumo`. A descrição da ferramenta não foi mudada para isso (veja "Lacunas") |
| Não cita lojista, cliente nem produto individual | Sim: só grupos e contagens |

Nas duas, o modelo tratou os números como associação, não como causa, e repetiu a ressalva da descrição dos fatores sobre quem fica de fora. Uma terceira execução, clicada no navegador (passo 6), teve o mesmo resultado: os três elos certos e nenhum canal.

## 3. Outras perguntas da Diretoria

Cada uma numa conversa nova, com o token de `diego.diretoria`.

**Executado pela API (26/11/2026):**

- `Qual canal tem a pior taxa de atraso?`: uma chamada a `diretoria_resumo` (107 ms), `fim` em 3,2 s. "O canal com a pior taxa de atraso é o **Mídia paga**, com **12,8%** (1.094 atrasos em 8.569 pedidos entregues), no período de 12 meses", com a tabela dos cinco canais (taxa de atraso e satisfação) na ordem da rota, e "O Mídia paga também tem a menor satisfação entre os canais, e é o que mais pesa em volume (9.214 pedidos)". Tudo confere com `/diretoria/resumo?periodo=12m`. Perguntado direto, o modelo chega ao canal.
- `Como a receita, a recompra, a satisfação e os atrasos evoluíram nos últimos 12 meses?`: duas chamadas, `diretoria_indicadores` (137 ms) e `diretoria_tendencia` (451 ms), `fim` em 8,5 s. A tabela do período contra o anterior confere (R$ 17,08 mi contra 13,54 mi, alta de cerca de 26%; 7,8% contra 1,4%; 4,09 contra 4,09; retenção 4,6%, 573 de 12.495, "não disponível" no anterior). Na leitura mês a mês, o pico de novembro (R$ 2,41 mi), a recompra de 3,5% em dezembro a 14,2% em novembro, a satisfação entre 4,01 e 4,14 e o atraso de novembro (4,1%, com a ressalva de que só 1.690 dos 2.173 pedidos estavam entregues) conferem com a tendência. A resposta lembrou que a taxa de um mês não se compara com a de 12 meses. **Dois deslizes de leitura:** disse que a receita "ficou entre R$ 1,1 mi e R$ 1,4 mi por mês", esquecendo dezembro de 2025 (R$ 2,05 mi), e que a recompra "subiu de forma contínua", quando junho (6,6%) ficou abaixo de maio (7,5%).

## 4. As negativas (RF-04, RF-17)

**O que se espera:** o assistente diz que não tem acesso, sem inventar número; o rastreio só com ferramentas do perfil (ou nenhuma); a auditoria sem chamada fora das ferramentas do perfil. A garantia não depende do modelo: o assistente só recebe as ferramentas do perfil de quem perguntou, e a camada da Diretoria não tem nenhuma linha de lojista, cliente, pedido ou produto.

**Executado pela API (26/11/2026)**, cada uma numa conversa nova:

- `diego.diretoria`, `Quais lojistas mais atrasam?`: uma chamada a `diretoria_resumo` (108 ms), `fim` em 3,9 s. A resposta abriu com "Não consigo identificar lojistas individualmente: o painel não oferece recorte por lojista" e ofereceu o recorte por canal, com a tabela dos cinco canais em 12 meses (taxa de atraso, entregues, atrasos e satisfação, iguais à rota) e "**Mídia paga** é o canal com mais atrasos, tanto em taxa quanto em volume". Nenhum nome de lojista. Dois detalhes: o modelo escreveu "canal de origem do lojista" (o painel diz só "canal"), e a tabela trocou a ordem de Orgânico e Prospecção ativa em relação à rota.
- `diego.diretoria`, `Quais são as avaliações do produto 1?`: nenhuma chamada, `fim` em 2,1 s. "Não tenho acesso às avaliações do produto 1. Eu consigo consultar apenas indicadores consolidados do marketplace [...] Esses números não são separados por produto, e não mostro avaliações individuais.", seguida da oferta da satisfação geral e da satisfação pela faixa de atraso.
- `ana.vendas`, `Qual a taxa de recompra por canal?`: nenhuma chamada, `fim` em 2,6 s. "Não tenho acesso a dados de **taxa de recompra** nem a dados de **canal** de venda.", seguida da lista do que as ferramentas de Vendas oferecem e de "Não consigo identificar clientes que compraram de novo, então não tenho como calcular a recompra."

As três terminaram em "não tenho acesso" (ou "não consigo identificar"), sem número inventado.

**A auditoria.** Todas as linhas das perguntas dos passos 2 a 4 (os horários da auditoria estão em UTC):

```
docker compose exec postgres psql -U dono -d auditoria -c "select id, to_char(horario,'HH24:MI:SS') h, nome_do_usuario, perfil, ferramenta, parametros, resultado from auditoria.chamada order by id"
```

```
 id |    h     | nome_do_usuario |  perfil   |          ferramenta           |     parametros     | resultado
----+----------+-----------------+-----------+-------------------------------+--------------------+-----------
  1 | 15:40:07 | Diego Almeida   | diretoria | diretoria_fatores_de_recompra | {"periodo": "12m"} | permitida
  2 | 15:40:27 | Diego Almeida   | diretoria | diretoria_fatores_de_recompra | {"periodo": "12m"} | permitida
  3 | 15:40:38 | Diego Almeida   | diretoria | diretoria_resumo              | {}                 | permitida
  4 | 15:40:47 | Diego Almeida   | diretoria | diretoria_indicadores         | {"periodo": "12m"} | permitida
  5 | 15:40:47 | Diego Almeida   | diretoria | diretoria_tendencia           | {"periodo": "12m"} | permitida
  6 | 15:41:20 | Diego Almeida   | diretoria | diretoria_resumo              | {"periodo": "12m"} | permitida
```

As linhas 1 e 2 são a pergunta sugerida; a 3, a do canal (sem `periodo`, valeu o padrão de 12 meses); a 4 e a 5, a da evolução; a 6, a dos lojistas. As perguntas das avaliações do produto e da recompra por canal (Ana) não deixaram linha. Nenhuma chamada fora das ferramentas da Diretoria, e nenhuma tentativa negada.

## 5. A matriz entre os quatro usuários (CA-01, CA-02)

**Rotas.** Com o token de cada um (`ana.vendas`, `bruno.produtos`, `carla.comercial` e `diego.diretoria`), as dezessete rotas de dados (quatro de Vendas, cinco de Produtos, quatro do Comercial e quatro da Diretoria, lidas do registro da API), com `?periodo=12m` e com um período inválido (`?periodo=xyz`).

**Executado em 26/11/2026:**

| Quem pediu | Vendas (4) | Produtos (5) | Comercial (4) | Diretoria (4) |
| --- | --- | --- | --- | --- |
| `ana.vendas` | 200 | 403 | 403 | 403 |
| `bruno.produtos` | 403 | 200 | 403 | 403 |
| `carla.comercial` | 403 | 403 | 200 | 403 |
| `diego.diretoria` | 403 | 403 | 403 | 200 |

Os 102 pedidos negados (26, 24, 26 e 26) receberam `403 {"erro":"Acesso negado."}`, a mesma negação em toda rota. Com o período inválido, o dono recebeu `400 {"erro":"Parâmetro inválido."}`, e os outros três o mesmo `403`: a negação vem antes da validação do parâmetro e não diz se o dado existe.

**Ferramentas.** Com o token do cliente `pulso-inspector` de cada um, `tools/list` cru por HTTP, e, para `diego.diretoria`, também pelo Inspector:

```
TOKEN=$(uv run python -m token_de_demonstracao diego.diretoria pulso-inspector)
npx @modelcontextprotocol/inspector@2.16.0 --cli http://localhost:8001/mcp --transport http --stored-auth-only --header "Authorization: Bearer $TOKEN" --method tools/list
```

**Executado em 26/11/2026** (Inspector com Node.js 24.20): `diego.diretoria` lista só `diretoria_indicadores`, `diretoria_fatores_de_recompra`, `diretoria_resumo` e `diretoria_tendencia`; `ana.vendas`, só as cinco `vendas_*`; `bruno.produtos`, só as cinco `produtos_*`; `carla.comercial`, só as quatro `comercial_*`. Nenhum perfil recebe mais a lista vazia.

A chamada direta de cada uma das dezoito ferramentas, crua, com o token de cada um, com os argumentos obrigatórios mínimos, e de uma ferramenta que não existe (`nao_existe`):

```
curl -s -X POST http://localhost:8001/mcp -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"diretoria_resumo","arguments":{"periodo":"12m"}}}'
```

| Quem chamou | `vendas_*` (5) | `produtos_*` (5) | `comercial_*` (4) | `diretoria_*` (4) |
| --- | --- | --- | --- | --- |
| `ana.vendas` | resultado | Ferramenta desconhecida. | Ferramenta desconhecida. | Ferramenta desconhecida. |
| `bruno.produtos` | Ferramenta desconhecida. | resultado | Ferramenta desconhecida. | Ferramenta desconhecida. |
| `carla.comercial` | Ferramenta desconhecida. | Ferramenta desconhecida. | resultado | Ferramenta desconhecida. |
| `diego.diretoria` | Ferramenta desconhecida. | Ferramenta desconhecida. | Ferramenta desconhecida. | resultado |

A ferramenta de outro perfil recebeu sempre `{"content":[{"text":"Ferramenta desconhecida.","type":"text"}],"isError":true}`, igual, letra por letra, à resposta de `nao_existe`. Na auditoria, as chamadas ficaram com o nome e o perfil de quem chamou: Ana Ribeiro, 5 `permitida` e 14 `negada`; Bruno Costa, 5 e 14; Carla Mendes, 4 e 15; Diego Almeida, 4 e 15 (as de outro perfil e a inexistente).

**Papéis do banco.** Conecte com cada papel (a senha é a do `backend/.env`):

```
docker compose exec postgres psql -h 127.0.0.1 -U diretoria -d marketplace
```

**Executado em 26/11/2026:**

| Papel | Comando | Resultado |
| --- | --- | --- |
| `diretoria` | `select periodo, contagem from diretoria.indicadores;` | 4 linhas: `12m 15379`, `24m 27301`, `30d 2173`, `90d 4726` |
| `diretoria` | `select * from vendas.pedido limit 1;` | `ERROR:  permission denied for schema vendas` |
| `diretoria` | `select * from produtos.produto limit 1;` | `ERROR:  permission denied for schema produtos` |
| `diretoria` | `select * from comercial.lead limit 1;` | `ERROR:  permission denied for schema comercial` |
| `diretoria` | `select * from dados_de_origem.pedido limit 1;` (e `cliente`, `lojista`) | `ERROR:  permission denied for schema dados_de_origem`, nos três |
| `diretoria` | `create temporary table t (id int);` | `ERROR:  cannot execute CREATE TABLE in a read-only transaction` |
| `diretoria` | conectar aos bancos `auditoria` e `historico` | `FATAL:  permission denied for database` (sem o privilégio `CONNECT`), nos dois |
| `vendas`, `produtos`, `comercial` | `select * from diretoria.indicadores limit 1;` | `ERROR:  permission denied for schema diretoria`, nos três |

A camada de leitura da Diretoria, lida pelo dono em `information_schema.columns`, tem cinco views: `indicadores` (o período, a contagem, os clientes com recompra, a receita, as avaliações, a satisfação, os retidos e os mesmos valores do período anterior, e a contagem de dois períodos antes), `tendencia` (período, `inicio` do ponto e as contagens e valores do ponto), `fatores_de_recompra` (período, bloco, grupo, contagem, clientes com recompra, satisfação), `resumo` (período, canal e as contagens e valores do canal) e `referencia` (`data_referencia`). Não há identificador, nome, e-mail, documento, endereço, cidade, UF nem comentário (RF-05). Toda view de indicadores tem a contagem do grupo, e a menor é bem maior que 1: 2.173 nos indicadores (4 linhas), 60 na tendência (80 linhas), 36 nos fatores (32 linhas) e 130 no resumo (20 linhas).

## 6. Conferência no navegador

Abra `http://localhost:5173` e entre como `diego.diretoria`. Confira, comparando com as rotas do passo 1 no mesmo período.

**Conferido no Chrome em 26/11/2026**, pelo agente, numa janela de 1.568 px de largura:

- **Entrada:** depois do login, a página "Painel da Diretoria", com "Olá, Diego.", o nome "Diego Almeida" e o perfil "Diretoria" na barra lateral e no topo, com o marcador do perfil em tom dourado. Não aparece "O painel chega em breve".
- **Cartões, em 12 meses:** **Receita** R$ 17.082.039,33, +26,1%; **Taxa de recompra** 7,8%, +6,4 p.p., "1.204 de 15.379 clientes compraram de novo"; **Satisfação** 4,09, +0,01, "Nota média de 11.594 avaliações"; **Retenção** 4,6%, sem variação, "573 de 12.495 clientes do período anterior compraram de novo". Conferem com `/diretoria/indicadores`. As três variações aparecem em verde, com seta para cima.
- **Tendência, em 12 meses:** "Tendência dos indicadores", "Por mês", quatro gráficos pequenos lado a lado (Receita, Taxa de recompra, Satisfação e Taxa de atraso), cada um com escala própria; o texto alternativo da receita traz os doze meses com os valores da rota (dezembro de 2025, R$ 2.046.457,04; janeiro de 2026, R$ 1.115.646,54; e assim por diante), e o da recompra começa em 3,5% e 4,2%, como a rota.
- **Fatores de recompra, em 12 meses:** três blocos, "Recompra pela primeira entrega" (No prazo 8,8%, Com atraso 0,0%), "Recompra pela primeira nota" (1 ou 2 0,8%, 3 10,2%, 4 ou 5 12,9%) e "Satisfação pela faixa de atraso" (4,28, 2,83 e 1,75), cada um com a frase de quem fica de fora. Em 24 meses, a dica da barra "No prazo" da primeira entrega mostrou "Taxa de recompra 5,6%, Clientes com recompra 1.365, Clientes do grupo 24.310", o tamanho do grupo da rota.
- **Resumo por canal do lojista:** as cinco linhas da tabela do passo 1, na mesma ordem e com os mesmos números (Mídia paga 9.214, R$ 8.836.743,17, 12,8%, 4,02, 7,9%; e assim por diante), com a frase "do canal que mais atrasa para o que menos atrasa" e "O cliente conta no canal do lojista da primeira compra".
- **"Canal" e nenhum lojista:** a palavra "origem" não aparece na página, nem nome de empresa (procurados no texto inteiro da página).
- **Troca de período:** todos os blocos acompanham, e o período fica no endereço (`?periodo=30d`, `90d`, `24m`). Em 30 dias: R$ 2.405.996,39 (+78,5%), 14,2% (+1,3 p.p.), 4,12 (+0,05) e retenção 0,8% (+0,1 p.p.), com 11 de 1.296; tendência "Por dia"; fatores 18,1% e 0,0%, 4,2%, 23,9% e 33,8%, 4,23, 2,80 e 2,00; resumo com Mídia paga 6,2% no topo e Indicação 0,0% no fim. Em 90 dias: R$ 5.015.756,51 (+30,4%), 12,5% (+4,3 p.p.), 4,10 (−0,01) e 5,4% (+3,3 p.p.); "Por semana"; fatores 14,6%, 1,5%, 21,7%, 22,7%, 4,26, 2,85 e 1,80; resumo com Mídia paga 10,4%. Em 24 meses: R$ 30.625.969,36, 5,0% e 4,09, os três sem variação, e a retenção "—", com a legenda "Sem período anterior nos dados"; "Por mês"; fatores 5,6%, 0,5%, 6,3%, 8,3%, 4,28, 2,84 e 1,75; resumo com Mídia paga 13,3%. Tudo igual às rotas do passo 1.
- **Assistente:** o painel lateral "Assistente PULSO, Perfil Diretoria" com a pergunta sugerida "Por que os clientes compram uma vez e não voltam?". Clicada (com o painel em 24 meses), a resposta chegou com os três elos em 12 meses (8,8% de 13.660 e 0% de 1.313; 0,8%, 10,2% e 12,9%; 4,28, 2,83 e 1,75), sem canal, como no passo 2: o assistente não recebe o período do painel e usa o padrão das ferramentas. No modo expandido, a lista de conversas mostrou as sete conversas do Diego (as seis dos passos 2 a 4 e esta), e o bloco "Como esta resposta foi obtida", aberto, mostrou `diretoria_fatores_de_recompra`, "concluída", 77 ms e o identificador da pergunta. Esc voltou do modo expandido ao painel lateral. A chamada ficou na auditoria (linha 83, Diego Almeida, `diretoria_fatores_de_recompra`, `permitida`).
- **Teclado:** com o foco no botão "12 meses", Enter trocou o período; Tab levou ao botão seguinte e depois ao gráfico de receita, com contorno de foco visível; a seta para a direita mostrou a dica do ponto seguinte ("Janeiro de 2026, Receita R$ 1.115.646,54"). Os gráficos têm o papel `application` e o texto alternativo com a série inteira.
- **Tela pequena:** como a janela do Chrome não aceitou ser redimensionada, o painel foi aberto num quadro de 390 px de largura dentro da mesma página (mesma origem, mesma sessão). A página não rola na horizontal (371 px de conteúdo em 387 px de janela); os quatro cartões ficam empilhados, com 339 px; os quatro gráficos pequenos da tendência ficam um embaixo do outro (mesma posição horizontal, 305 px de largura); e a tabela do resumo, com 980 px, rola na horizontal dentro do contêiner dela (337 px, `overflow-x: auto`).
- **Estados de carregamento, vazio e erro**, provocados no quadro de 390 px trocando a resposta das rotas `/diretoria/*` dentro da página (o `fetch` da página foi interceptado; a API não foi tocada): com a resposta atrasada em 15 s, os quatro blocos mostraram o esqueleto e anunciaram "Carregando os indicadores…", "Carregando a tendência dos indicadores…", "Carregando os fatores de recompra…" e "Carregando o resumo por canal…"; com `500`, cada bloco mostrou "Não foi possível carregar …", "O servidor não respondeu como esperado. Os outros blocos do painel não são afetados." e o botão "Tentar de novo" (quatro botões); com as contagens zeradas na tendência, nos fatores e no resumo, os três blocos mostraram o estado vazio ("Nenhum pedido aprovado no período", "Nenhum cliente nem avaliação no período" e "Nenhum pedido no período", cada um com "Escolha um período maior").
- **Troca de usuário:** depois de **Sair**, a entrada como `ana.vendas` mostrou o "Painel de Vendas" (16.795 pedidos, R$ 17.082.039,33, a mesma receita da Diretoria, taxa de atraso de 9,0%, aprovação de 96,0%); como `bruno.produtos`, o "Painel de Produtos" (2.000 produtos no catálogo, nota média 4,09, a mesma satisfação da Diretoria, 20 produtos mal avaliados, 11.594 avaliações); como `carla.comercial`, o "Painel Comercial" (746 leads, 126 novos lojistas, 16,9% de conversão, Mídia paga como principal canal). Quatro usuários, quatro painéis diferentes (CA-01). As três entradas foram na primeira tentativa.
- **Uma observação visual:** em largura de desktop, o cartão da tendência estica até a altura da coluna dos três blocos de fatores, e fica um espaço vazio grande embaixo dos quatro gráficos pequenos. Não esconde nem corta nada.

## 7. O tempo das rotas (RNF-05)

Dentro de `backend/`:

```
uv run python tests/demonstracao.py tempos 24m diretoria
```

**Executado em 26/11/2026**, contra a API do compose (cinco pedidos por rota, depois de um de aquecimento):

| Rota | Mediana | Máximo |
| --- | ---: | ---: |
| `/diretoria/indicadores` | 57 ms | 61 ms |
| `/diretoria/fatores-de-recompra` | 85 ms | 87 ms |
| `/diretoria/resumo` | 124 ms | 124 ms |
| `/diretoria/tendencia` | 474 ms | 529 ms |

Na mesma medição, as de Vendas ficaram entre 4 e 63 ms de mediana. Todas abaixo da meta de 3 s, e a decisão de views comuns, não materializadas, fica como está (ADR 0011). A tendência é a mais lenta: as views calculam os quatro períodos a cada leitura, e a da tendência cruza as três áreas ponto a ponto; os 474 ms são bem mais que os cerca de 20 ms da medição citada no ADR, que era de um cruzamento só. O teste de tempo da suíte (`test_tempo_das_rotas.py`) mede as mesmas rotas contra a meta.

## Lacunas

O que este roteiro **não** conferiu, ou conferiu diferente do esperado:

1. **O canal na pergunta sugerida.** Nas três execuções (duas pela API e uma no navegador), o modelo padrão respondeu com os três elos certos, mas não chamou `diretoria_resumo` e não apontou Mídia paga como o canal que mais atrasa. A descrição da ferramenta não foi mudada para ele acertar. Perguntado direto ("Qual canal tem a pior taxa de atraso?") ou pelos lojistas, ele chega a Mídia paga com os números certos.
2. **O período do painel não chega ao assistente.** Com o painel em 24 meses, a pergunta sugerida foi respondida com os números de 12 meses, o padrão das ferramentas. É o comportamento dos outros perfis, não uma mudança desta entrega.
3. **Deslizes de leitura do modelo padrão**, não de dado copiado: na pergunta da evolução, a faixa de receita mensal esqueceu dezembro de 2025 e a recompra foi dita "contínua" com uma queda em junho; na dos lojistas, "canal de origem" e a ordem de dois canais trocada.
4. **Tela pequena** foi conferida num quadro de 390 px dentro da página, não numa janela ou num aparelho de 390 px: a janela do Chrome não aceitou o redimensionamento.
5. **Estados de carregamento, vazio e erro** foram provocados trocando a resposta das rotas dentro da página, não com a API ou o banco fora do ar; o vazio dos cartões não foi provocado (só os três blocos que têm estado vazio).
6. **Leitor de tela.** Foram conferidos o foco, o texto alternativo e os rótulos pela árvore de acessibilidade, não com um leitor de tela de verdade.
7. **O tom exato do dourado** não foi medido; o que se viu foi o marcador do perfil em tom dourado.
8. **O limite de frequência com o Diego** não foi provocado à mão; é genérico por usuário e está nos testes (`test_limite_de_frequencia.py`).
9. **A chamada negada com o modelo real** continua sem ser vista: diante dos pedidos de lojista e de produto, o modelo não tentou ferramenta de outro perfil.
10. **Claude e ChatGPT** com o perfil Diretoria ficam para a entrega 7.

## Testes da entrega

Com o ambiente no ar e o limite alto no `mcp` (seção Testes do README), dentro de `backend/`, `uv run pytest`; no `frontend/`, `npm test`, `npm run typecheck`, `npm run lint` e `npm run build`. O modelo real não aparece na suíte.

Os testes da entrega: `test_camada_diretoria.py`, `test_indicadores_da_diretoria.py`, `test_tendencia_da_diretoria.py`, `test_fatores_de_recompra.py` e `test_resumo_da_diretoria.py`, além das matrizes, que crescem pelos registros (`test_matriz_de_papeis.py`, `test_matriz_de_isolamento.py`, `test_isolamento_do_assistente.py`, `test_registro_de_ferramentas.py` e `test_tempo_das_rotas.py`) e dos testes do Inspector e do registro dinâmico, agora parametrizados pelos quatro perfis. No Vitest: os validadores e os blocos do painel da Diretoria (`frontend/src/diretoria/`) e a pergunta sugerida da Diretoria.

O resultado da suíte completa, executada uma vez no fechamento desta entrega, está na situação da 10 em `docs/ROADMAP.md`.

## Encerrar

```
docker compose down -v
```

Apaga também o histórico e a auditoria.
