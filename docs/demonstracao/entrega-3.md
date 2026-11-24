# Roteiro de demonstração: entrega 3, Vendas na tela

Este roteiro mostra a entrega 3 inteira, na ordem do roadmap: o painel de Vendas com os dados do banco, a mesma negação para os outros três perfis e o tempo de cada rota de Vendas contra a meta de 3 segundos do RNF-05. Cada passo traz o comando e o resultado esperado com a configuração padrão (semente 20261130, data de referência 30/11/2026). Os comandos são os mesmos no PowerShell e no bash e rodam na raiz do projeto, salvo quando o passo indica `backend/` ou `frontend/`.

Pré-requisitos: Docker com Docker Compose, [uv](https://docs.astral.sh/uv/), Node.js 24 (para a suíte do frontend) e um navegador.

## 1. Preparar a configuração e subir do zero

```
cp backend/.env.example backend/.env
docker compose down -v
docker compose up -d --build --wait
```

O `backend/.env` é o mesmo da entrega 2: a senha do papel de Vendas (`SENHA_DO_PAPEL_VENDAS`), que a API agora usa para ler o banco, já estava no exemplo. O compose sobe o Postgres, roda a carga, sobe o Keycloak, a API e o frontend, e termina com os contêineres `Healthy` e a carga `Exited`, como na entrega 2.

A carga grava a data de referência no próprio banco. A API não a lê da configuração: as consultas a leem da camada de leitura de Vendas.

## 2. O painel de Vendas com os dados do banco

Abra `http://localhost:5173` e entre como `ana.vendas` (senha em `SENHA_DO_USUARIO_VENDAS`). A aplicação abre o **Painel de Vendas** com o período padrão de 12 meses, na URL como `?periodo=12m`. De cima para baixo:

- o cabeçalho com o seletor de período: **30 dias**, **90 dias**, **12 meses** e **24 meses**;
- quatro indicadores, cada um com a variação em relação aos 12 meses anteriores:

| Indicador | Valor em 12 meses | Variação | Legenda |
| --- | --- | --- | --- |
| Pedidos realizados | 16.795 | ↑ +27,2% (verde) | Inclui pagamentos recusados |
| Receita | R$ 17.082.039,33 | ↑ +26,1% (verde) | Pagamentos aprovados, com frete |
| Taxa de atraso | 9,0% | ↓ -1,2 p.p. (verde: o atraso caiu) | 1.411 atrasos entre os pedidos entregues |
| Taxa de aprovação | 96,0% | 0,0 p.p. (neutra, sem seta) | Pedidos com pagamento aprovado |

- **Evolução de pedidos e receita**, por mês: barras de pedidos e linha de receita, com um eixo para cada;
- **Situação das entregas**, em barras horizontais: Em trânsito 436, Prazo vencido 57, Entregue no prazo 14.211, Entregue com atraso 1.411, com a nota de que pedidos com pagamento recusado não têm entrega;
- **Pedidos recentes**: os 20 pedidos mais recentes, do 29999 para trás, com data e hora de Brasília, cidade e UF do cliente, lojista, rota, valor em reais e as situações do pagamento e da entrega em chips discretos.

As variações das taxas aparecem em pontos percentuais (`p.p.`); as de pedidos e receita, em percentual. Verde é melhora, vermelho é piora: a taxa de atraso melhora quando cai. Uma variação que arredonda para zero, como a da taxa de aprovação (-0,03 p.p.), fica neutra, sem cor nem seta.

**Troque o período.** Clique em **30 dias**: a URL vira `?periodo=30d`, os quatro blocos mostram o esqueleto ao mesmo tempo e voltam com os dados de novembro de 2026, e a evolução passa a ser por dia. Em **90 dias** ela é por semana; em **24 meses**, por mês de novo, com 29.999 pedidos e R$ 30.625.969,36 de receita. Em 24 meses os indicadores não mostram variação: não há dados no período anterior.

**Período inválido na URL.** Abra `http://localhost:5173/?periodo=7d`: o painel abre em 12 meses, sem mensagem de erro.

**Recarregue (F5)** com `?periodo=90d`: o painel volta em 90 dias.

## 3. O painel nas quatro faixas de largura (FE §11)

Com o painel aberto em 24 meses, reduza a largura do navegador (ou use as ferramentas do navegador, modo responsivo). A revisão desta entrega mediu cada faixa:

| Largura | Indicadores | Gráficos | Tabela |
| --- | --- | --- | --- |
| ≥ 1280 px (desktop) | 4 em linha; a receita inteira, com o valor reduzido até 21 px a 1280 px | lado a lado, 8/12 e 4/12, com a mesma altura | inteira ou com rolagem só dentro da moldura |
| 1024 a 1279 px (laptop) | 2×2 | empilhados | rolagem horizontal dentro da moldura |
| 768 a 1023 px (tablet) | 2×2; a sidebar vira gaveta, aberta pelo botão de menu | empilhados | rolagem horizontal dentro da moldura |
| 480 a 767 px (celular) | 2×2, margens de 16 px; o seletor de período ocupa a linha | empilhados, uma coluna | rolagem horizontal, com a coluna do pedido fixa |
| < 480 px (celular pequeno) | 1 coluna estreita, como o FE §11 permite: a receita não cabe em meio cartão sem reduzir o texto | empilhados | idem |

Em nenhuma largura, de 320 px em diante, a página ganha rolagem horizontal: só a tabela rola, dentro da própria moldura. Abaixo de 480 px, o botão **Sair** mostra só o ícone e a trilha da topbar some.

## 4. Os estados de cada bloco (FE §10)

Cada bloco carrega, falha e fica vazio por conta própria:

- **Carregando:** ao trocar o período, cada bloco mostra um esqueleto do mesmo tamanho do conteúdo (cartões, área do gráfico, linhas da tabela), sem a tela piscar.
- **Erro:** pare a API com `docker compose stop api` e troque o período. Cada bloco mostra `Não foi possível carregar…` com o botão **Tentar de novo**, sem cobrir a página. Suba a API com `docker compose start api` e clique em **Tentar de novo** num bloco: só ele volta. O foco do teclado (Tab) mostra um anel visível no botão e no seletor de período.
- **Vazio e negado:** a carga padrão não produz período sem pedidos, e só o perfil Vendas abre o painel. Os dois estados existem em cada bloco (`Nenhum pedido no período`; `Acesso não disponível`, sério e neutro, para uma resposta 403) e foram conferidos na revisão forçando as respostas da API no navegador.

**Sessão vencida.** A sessão termina depois de 30 minutos sem uso, como na entrega 2. Com o painel aberto, a próxima chamada que receber 401 leva de volta à tela de login.

## 5. Os outros três perfis

Clique em **Sair** e entre como `bruno.produtos`, `carla.comercial` e `diego.diretoria`. Cada um vê o próprio painel com o aviso **O painel chega em breve**, como na entrega 2, e nunca o painel de Vendas.

Pela linha de comando, cada usuário chama as quatro rotas de Vendas da API do ambiente com o próprio token, obtido pelo mesmo fluxo do navegador. Dentro de `backend/`:

```
uv sync --locked
uv run python tests/demonstracao.py vendas ana.vendas
```

```
token de ana.vendas: perfil=vendas
GET /vendas/indicadores?periodo=12m -> 200 16795 pedidos, receita 17082039.33, aprovação 0.960
GET /vendas/evolucao?periodo=12m -> 200 12 pontos por mes
GET /vendas/situacao-das-entregas?periodo=12m -> 200 Em trânsito 436, Prazo vencido 57, Entregue no prazo 14211, Entregue com atraso 1411
GET /vendas/pedidos-recentes?periodo=12m -> 200 20 pedidos, o mais recente 29999
```

```
uv run python tests/demonstracao.py vendas bruno.produtos
```

```
token de bruno.produtos: perfil=produtos
GET /vendas/indicadores?periodo=12m -> 403 {"erro": "Acesso negado."}
GET /vendas/evolucao?periodo=12m -> 403 {"erro": "Acesso negado."}
GET /vendas/situacao-das-entregas?periodo=12m -> 403 {"erro": "Acesso negado."}
GET /vendas/pedidos-recentes?periodo=12m -> 403 {"erro": "Acesso negado."}
```

Com `carla.comercial` e `diego.diretoria`, a saída é a mesma, trocando a primeira linha. A negação é idêntica em toda rota e para todo perfil: não diz se os dados existem nem qual verificação negou. Ela vem antes de qualquer validação de parâmetro e de qualquer conexão com o banco, e a suíte do passo 7 prova as duas coisas.

O período é o segundo argumento, opcional: `vendas ana.vendas 24m`. Um período fora da enumeração recebe a resposta genérica, sem eco do valor:

```
uv run python tests/demonstracao.py vendas ana.vendas 7d
```

```
token de ana.vendas: perfil=vendas
GET /vendas/indicadores?periodo=7d -> 400 {"erro": "Parâmetro inválido."}
...
```

Com `bruno.produtos` e o mesmo `7d`, a resposta continua sendo o 403: quem não tem acesso não descobre nada sobre os parâmetros.

## 6. O tempo de cada rota em 24 meses (RNF-05)

Dentro de `backend/`:

```
uv run python tests/demonstracao.py tempos
```

O comando faz o login como `ana.vendas`, aquece cada rota com um pedido e mede cinco pedidos por rota na API do ambiente, no período de 24 meses, com token validado, conexão do pool e consulta no banco. Medido em 24/11/2026, num Windows 11 com Docker Desktop, contra a carga padrão (29.999 pedidos em 24 meses):

```
5 pedidos por rota, periodo=24m, meta 3 s (RNF-05)
/vendas/indicadores              mediana    59 ms  máximo    67 ms
/vendas/evolucao                 mediana    64 ms  máximo    65 ms
/vendas/situacao-das-entregas    mediana    37 ms  máximo    38 ms
/vendas/pedidos-recentes         mediana     4 ms  máximo     4 ms
```

Todas as rotas ficam abaixo de 0,1 s, longe da meta de 3 s, sem nenhum índice novo na carga. Os números variam com a máquina; a meta é confirmada de novo na entrega 11. Cada sessão do papel de Vendas no banco tem `statement_timeout` de 3 s: uma consulta lenta falha com a resposta genérica `503 {"erro": "Serviço indisponível."}` em vez de prender a conexão.

A prova automatizada é `test_cada_rota_responde_em_menos_de_3_segundos_em_24_meses`, em `test_rotas_de_vendas.py`: um caso por rota, com a API de verdade, token real e banco carregado.

## 7. A suíte

Com o ambiente no ar, dentro de `backend/`:

```
uv run pytest
```

Resultado esperado: `285 passed`, em cerca de oito minutos. Como na entrega 2, a suíte recarrega o banco e reinicia o Keycloak, então ela vem depois dos passos no navegador. Os testes novos da entrega 3:

| Arquivo | O que verifica |
| --- | --- |
| `test_rotas_de_vendas.py` | Os quatro usuários contra as quatro rotas: 200 só para Vendas, o mesmo 403 para os outros; a ordem 401, 403, 400; o 400 genérico sem eco; a negação antes do banco; perfil sem credencial negado; erro de banco sem nomes internos; menos de 3 s por rota em 24 meses |
| `test_perfil_das_rotas.py` | Toda rota declara um perfil ou está na lista de rotas só autenticadas (RS-05) |
| `test_indicadores_de_vendas.py` | Os quatro indicadores e o período anterior nos quatro períodos, contra consultas independentes |
| `test_evolucao_de_vendas.py` | O agrupamento por dia, semana e mês no horário de Brasília, com dias, semanas ou meses sem pedido em zero |
| `test_situacao_das_entregas.py` | As quatro situações, sempre todas, contra uma consulta independente |
| `test_pedidos_recentes.py` | Os 20 pedidos mais recentes, sem identificador de cliente |
| `test_camada_vendas.py` | A view da data de referência, lida pelo papel de Vendas, também com `DATA_REFERENCIA` sobreposta |

No frontend, dentro de `frontend/`, as funções puras (formatação, período da URL, variação e validação das respostas) rodam no Vitest:

```
npm ci
npm test
```

Resultado esperado: `Test Files  8 passed (8)` e `Tests  98 passed (98)`.

## 8. A integração contínua roda em um pull request

Todo pull request para `homolog` ou `main` roda os dois checks da entrega 2. O **Frontend** ganhou o passo `npm test` (Vitest), entre o lint e o build.

## Encerrar

```
docker compose down -v
```
