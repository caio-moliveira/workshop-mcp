# Roteiro de demonstração: entrega 5b, chat expandido, rastreio e histórico

Este roteiro mostra o que a 5b acrescenta ao assistente: as conversas ficam gravadas no servidor e só o dono as reabre (o **histórico**, RF-18); cada resposta traz o bloco "Como esta resposta foi obtida", com as chamadas que a produziram (o **rastreio**); o painel tem um modo expandido para respostas longas, com subtítulos e tabelas; e um identificador por pergunta liga, nos logs, a pergunta na API à chamada no servidor MCP e à consulta no banco (RNF-06). Os comandos rodam na raiz do projeto, salvo quando o passo indica `backend/`. Onde o PowerShell e o bash diferem, o passo mostra os dois.

Pré-requisitos: Docker com Docker Compose, [uv](https://docs.astral.sh/uv/), um navegador e uma chave da API da Anthropic (o provedor do modelo padrão).

**O que foi conferido e como.** Em 25/11/2026, os passos 2 a 8 foram executados pela API, com o modelo real (`anthropic:claude-haiku-5-5`, o padrão): o token de cada usuário veio do comando de token de demonstração, a pergunta foi enviada em `POST /assistente`, como o painel faz, o fluxo de eventos foi lido até o fim e as conversas foram lidas, listadas e apagadas pelas rotas que o painel usa (`GET /conversas`, `GET /conversas/{id}` e `DELETE /conversas/{id}`). Os números foram conferidos com as rotas do painel de Vendas; os identificadores, com `docker compose logs`. A parte visual (o modo expandido, a lista de conversas, o bloco de rastreio aberto e fechado, a tabela no painel lateral, os dois usuários no navegador) **não foi executada**: ela pede um navegador e está marcada abaixo como **conferência manual**, para o apresentador. As respostas do modelo mudam a cada execução; o que este roteiro anota é o resultado observado e o que deve se repetir.

**O ambiente da execução foi subido do zero**, como no passo 1: `docker compose down -v` e `docker compose up -d --build --wait`, com o código da branch depois das correções da revisão (a resposta achada pelo identificador da pergunta, o 404 para o identificador de conversa fora do formato). Antes da primeira pergunta, o banco `historico` tinha 0 conversas e 0 itens, e a auditoria, 0 linhas; as listas e contagens abaixo são só desta execução.

## 1. Configurar e subir

```
cp backend/.env.example backend/.env
```

No `backend/.env`, preencha `ANTHROPIC_API_KEY` e troque as senhas. Esta entrega acrescenta duas variáveis; quem já tem um `backend/.env` da 5a precisa acrescentá-las e recriar o ambiente:

| Variável | O que é |
| --- | --- |
| `SENHA_DO_PAPEL_HISTORICO` | A senha do papel `historico`, com que a API lê, grava e apaga as conversas no banco `historico`, e só nele (ADR 0009). A carga cria o banco, o papel e as tabelas se faltarem e reaplica a senha, sem apagar o que há |
| `SENHA_DO_USUARIO_VENDAS_VITOR` | A senha de `vitor.vendas` (Vitor Nunes), o segundo usuário de demonstração de Vendas |

Suba do zero:

```
docker compose down -v
docker compose up -d --build --wait
```

O `down -v` é o único jeito de apagar o histórico, e é também como uma mudança na estrutura do banco `historico` chega a um ambiente já criado.

### Como perguntar pelo terminal

Como no roteiro da 5a, emita o token da aplicação dentro de `backend/` (vale 5 minutos):

PowerShell:

```
$TOKEN = uv run python -m token_de_demonstracao ana.vendas pulso-web
```

bash:

```
TOKEN=$(uv run python -m token_de_demonstracao ana.vendas pulso-web)
```

O corpo da pergunta mudou: leva a `pergunta` e, para continuar uma conversa, o `id_da_conversa`. Sem ele, nasce uma conversa nova. A conversa não é mais reenviada; a `conversa` da 5a no corpo recebe 400.

bash:

```
curl -sN -X POST http://localhost:8000/assistente -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"pergunta":"O que está causando os atrasos?"}'
```

PowerShell (o corpo num arquivo em UTF-8 sem BOM, para o acento chegar inteiro):

```
[IO.File]::WriteAllText("$PWD\pergunta.json", '{"pergunta":"O que está causando os atrasos?"}')
curl.exe -sN -X POST http://localhost:8000/assistente -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data-binary "@pergunta.json"
```

O fluxo ganhou dois eventos. O primeiro é sempre `conversa`, com o identificador da conversa e o da pergunta; cada chamada de ferramenta terminada sai como `chamada`, com a ferramenta, o desfecho e a duração medida pela API:

```
event: conversa
data: {"id_da_conversa": "72b298e5-...", "id_da_pergunta": "aeb93741-..."}

event: estado
data: {"estado": "consultando"}

event: chamada
data: {"ferramenta": "vendas_atrasos", "desfecho": "concluida", "milissegundos": 64}

event: texto
data: {"texto": "..."}
...
event: fim
data: {}
```

As rotas do histórico, com o mesmo token:

```
curl -s http://localhost:8000/conversas -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8000/conversas/<id_da_conversa> -H "Authorization: Bearer $TOKEN"
curl -s -X DELETE http://localhost:8000/conversas/<id_da_conversa> -H "Authorization: Bearer $TOKEN"
```

No PowerShell, `curl.exe` no lugar de `curl`.

## 2. A pergunta sugerida e o bloco de rastreio

**Conferência manual (navegador).** Abra `http://localhost:5173`, entre como `ana.vendas` e clique em **Assistente**. O cabeçalho do painel lateral tem **Nova conversa**, **Conversas**, **Expandir o assistente** e **Fechar o assistente**. Clique na pergunta sugerida, **O que está causando os atrasos?**. Enquanto a resposta chega, um indicador discreto mostra "Preparando a resposta…" ou "Consultando os dados…". Abaixo da resposta terminada fica o bloco **Como esta resposta foi obtida**, fechado. Abra o bloco: uma linha por chamada, com a ferramenta (`vendas_atrasos`), "concluída" e a duração em ms, e no fim `Pergunta <identificador>`. Anote esse identificador para o passo 7.

**Executado pela API (25/11/2026).** Resultado: 200; o evento `conversa` primeiro (conversa `72b298e5-...`, pergunta `aeb93741-...`); dois `estado` e duas `chamada` (`vendas_atrasos`, `concluida`, 64 ms cada) 2,1 s depois dele; 119 eventos `texto` e `fim` 7,7 s depois do `conversa`. A auditoria mostra as duas chamadas, por rota e por lojista (o modelo não passou o período, e valeu o padrão, 12 meses). A resposta, resumida:

> **Resumo:** os atrasos não vêm de uma única causa. Os dados mostram onde eles se concentram, mas não o motivo de cada um. No período, foram **1.411 atrasos em 15.622 pedidos entregues** (taxa de **9,0%**).
>
> **Lojistas:** a concentração é maior aqui. **Vasconcelos** responde por cerca de 23% dos atrasos, com taxa de 18,4%. [...] **Siqueira** tem taxa de 30,1% e cerca de 12% dos atrasos. **Fogaça** (34,4%), **Pinto Pires** (29,3%) e **Casa Grande da Cunha** (29,0%) têm taxas altas, mas participação menor no total.
>
> **Rotas:** o atraso está mais espalhado. São 255 rotas com atraso. **SP → SP** tem o maior número de atrasos (cerca de 9% do total), mas taxa de 5,3%, abaixo da média. **PE → SP** tem taxa de 19,2% [...] **SP → AM** (22,1%), **SP → PA** (19,0%), **SP → CE** (15,8%) e **SP → PE** (15,3%).
>
> **Leitura:** [...] Para confirmar, seria preciso olhar transportadora, prazo prometido e estoque, dados que não tenho acesso por esta ferramenta.

A conversa lida depois (`GET /conversas/72b298e5-...`) trouxe o título "O que está causando os atrasos?", a pergunta e a resposta com `"situacao": "concluida"`, o `id_da_pergunta` `aeb93741-...` (o mesmo do evento `conversa`) e o mesmo rastreio do fluxo: duas chamadas a `vendas_atrasos`, `concluida`, 64 ms.

**Os números conferem com o painel.** Nas rotas da API que o painel de Vendas usa, com o período **12 meses**:

| Na resposta | No painel e nas rotas | Confere |
| --- | --- | --- |
| Período de 12 meses (dito na resposta do passo 3: 1/12/2025 a 30/11/2026) | `periodo` de `/vendas/situacao-das-entregas`: 2025-12-01 a 2026-11-30 | Sim |
| Taxa de atraso 9,0% | Indicador "Taxa de atraso": `taxa_de_atraso.atual` 0,0903 em `/vendas/indicadores` | Sim |
| 1.411 atrasos | `taxa_de_atraso.atrasos` 1411; "Entregue com atraso" 1411 | Sim |
| 15.622 entregues | "Entregue no prazo" 14.211 + "Entregue com atraso" 1.411 = 15.622 | Sim |

Os números por lojista e por rota não estão no painel: vêm só de `vendas_atrasos`. Os que coincidem com os conferidos com a ferramenta chamada direto no roteiro da 5a, com os mesmos dados (Vasconcelos 18,4% e cerca de 23%, que é 323 ÷ 1.411; Siqueira 30,1%; SP → SP 5,3%; PE → SP 19,2%; 255 rotas com atraso), batem; os das rotas também batem com a tabela do passo 3. Os outros (Siqueira "cerca de 12% dos atrasos", Fogaça 34,4%, Pinto Pires 29,3%, Casa Grande da Cunha 29,0%) não foram conferidos com a ferramenta: nesta execução, a ferramenta não foi chamada à parte.

## 3. Uma resposta longa, com tabela, no modo expandido

**Conferência manual (navegador).** Na mesma conversa, clique em **Expandir o assistente**. O painel passa a cobrir a área de conteúdo, ao lado da barra lateral, com a lista de conversas numa coluna à esquerda e a conversa numa coluna central de cerca de 820 px, e a conversa em andamento continua na tela. Pergunte `Compare as rotas com mais atraso em uma tabela`. Confira:

- a tabela compacta, com subtítulos, lida sem aperto na coluna central;
- o bloco "Como esta resposta foi obtida" também nesta resposta;
- **Recolher o assistente** (ou Esc) volta ao painel lateral com a mesma conversa; ali a tabela larga rola na horizontal, sem alargar o painel; outro Esc fecha o painel;
- com a conversa vazia, no modo expandido, o cabeçalho editorial "O que você quer saber sobre Vendas?" e a sugestão em linha, com seta, não em chip;
- o texto digitado no campo continua lá ao expandir e recolher; Tab percorre o cabeçalho, a lista e o campo, sem alcançar a página atrás.

Abaixo de 768 px não há botão de expandir: o painel ocupa a tela inteira, e **Conversas** troca a conversa pela lista.

**Executado pela API (25/11/2026)**, como continuação da conversa do passo 2 (com o `id_da_conversa` dela): 200; o `conversa` com a mesma conversa e um identificador de pergunta novo (`7212f028-...`); uma chamada a `vendas_atrasos`, por rota (46 ms); 95 trechos e `fim` 5,2 s depois do `conversa`. A resposta abriu com "No período de **1/12/2025 a 30/11/2026** (12 meses), estas são as 10 rotas com mais atrasos. Ordenei pelo número de atrasos. Há 255 rotas com atraso ao todo." e veio em tabela Markdown:

| Rota | Entregues | Atrasos | Taxa de atraso | Participação no total |
|---|---:|---:|---:|---:|
| SP → SP | 2.270 | 121 | 5,3% | 8,6% |
| SP → RJ | 935 | 61 | 6,5% | 4,3% |
| PE → SP | 266 | 51 | 19,2% | 3,6% |
| SP → MG | 634 | 40 | 6,3% | 2,8% |
| SP → RS | 283 | 38 | 13,4% | 2,7% |
| SP → CE | 203 | 32 | 15,8% | 2,3% |
| SP → PE | 196 | 30 | 15,3% | 2,1% |
| SP → AM | 131 | 29 | 22,1% | 2,1% |
| SP → PA | 142 | 27 | 19,0% | 1,9% |
| SP → BA | 273 | 25 | 9,2% | 1,8% |

seguida de uma **Leitura** em três itens. As taxas batem com atrasos ÷ entregues em cada linha, e as participações com atrasos ÷ 1.411; as linhas são as mesmas, com os mesmos valores, da execução anterior deste roteiro. Um deslize de conta no último item: "As 10 rotas listadas somam cerca de 35% dos atrasos do período". Somam 454 atrasos, 32,2% de 1.411 (a soma das participações da própria tabela). O modelo se corrigiu sozinho na continuação do passo 4.

## 4. Recarregar a página e reabrir a conversa

**Conferência manual (navegador).** Recarregue a página e abra o assistente: ele abre numa conversa nova e vazia, com a pergunta sugerida. Clique em **Conversas** (ou expanda): a conversa dos passos 2 e 3 está no topo da lista, com o título "O que está causando os atrasos?". Abra-a: as perguntas, as respostas, a tabela e os blocos de rastreio estão como estavam. Faça uma pergunta de continuação; o assistente entende o contexto.

**Executado pela API (25/11/2026).** Depois da recarga do passo 8, a leitura da conversa trouxe os quatro itens (duas perguntas e duas respostas `concluida`, com os identificadores `aeb93741-...` e `7212f028-...` e o rastreio de cada uma: duas chamadas de 64 ms na primeira, uma de 46 ms na segunda). A continuação `e qual dessas rotas teve a maior taxa?` com o `id_da_conversa` dela: 200, nenhuma chamada, 21 trechos e `fim` 3,9 s depois do `conversa`:

> A rota com maior taxa entre as 10 listadas é **SP → AM**, com **22,1%** de atrasos: 29 atrasos em 131 pedidos entregues.
>
> Corrijo um erro na resposta anterior: as 10 rotas somam cerca de **32%** dos atrasos do período, não 35%.

O contexto veio do banco (a tabela da resposta anterior), não do navegador, e a correção está certa (32,2%). Lida de novo, a conversa ficou com seis itens; a terceira resposta, `concluida`, com o identificador da sua pergunta e `"rastreio": []`. Na execução anterior deste roteiro, a continuação "corrigiu" uma afirmação verdadeira, dizendo que não tinha consultado uma ferramenta que a auditoria mostra que consultou: o modelo recebe da conversa gravada só os textos de pergunta e resposta, sem as chamadas. Desta vez não aconteceu, mas a causa continua; fica anotada como lacuna no roadmap.

## 5. Nova conversa e apagar

**Conferência manual (navegador).** Clique em **Nova conversa**: a conversa some da tela e aparece a pergunta sugerida; a anterior continua na lista. Pergunte algo, abra **Conversas** e apague a conversa nova pelo botão da linha ("Apagar a conversa ..."); confirme no diálogo ("Não dá para desfazer."). Ela some da lista; se era a conversa aberta, o painel volta a uma conversa nova.

**Executado pela API (25/11/2026).** Uma pergunta sem `id_da_conversa`, `Quantos pedidos foram realizados nos últimos 90 dias?`, abriu a conversa `cdf6b10a-...`: uma chamada a `vendas_indicadores` (37 ms) e `fim` 1,6 s depois do `conversa`:

> Nos últimos 90 dias (de 02/09/2026 a 30/11/2026), foram realizados **4.962 pedidos**.
>
> No período anterior de mesmo tamanho, foram 3.726 pedidos, então houve um aumento de cerca de 33%.

Confere com o painel no período **90 dias**: `pedidos_realizados` 4962 e 3726, período de 2026-09-02 a 2026-11-30, e 4.962 ÷ 3.726 = 1,33.

Antes de apagar, a lista da Ana tinha as duas conversas dela, a mais recente no topo ("Quantos pedidos foram realizados nos últimos 90 dias?" e "O que está causando os atrasos?"). `DELETE /conversas/cdf6b10a-...` respondeu 204; a leitura dela passou a dar `404 {"erro":"Conversa não encontrada."}`, um segundo `DELETE` também deu 404, e a lista ficou só com a conversa dos passos 2 e 3. A auditoria tinha 4 linhas antes do `DELETE` (as três chamadas dos passos 2 e 3 e a desta pergunta) e continuou com 4 depois: apagar uma conversa não apaga as chamadas dela da auditoria (ADR 0009); a chamada desta pergunta continua lá (passo 9).

## 6. Um usuário não vê o histórico do outro

**Conferência manual (navegador).** Saia e entre como `vitor.vendas`. Abra o assistente e **Conversas**: as conversas da Ana não aparecem. Faça uma pergunta, saia, entre como `ana.vendas` de novo: a conversa do Vitor não aparece na lista dela, e as dela continuam lá. Repita com `diego.diretoria` (outro perfil): a lista dele não mostra as de Vendas, e a dele não aparece para a Ana. Num navegador só, use uma janela anônima para o segundo usuário, ou saia entre um e outro.

**Executado pela API (25/11/2026).** Vitor perguntou `Qual foi a receita e o ticket médio nos últimos 30 dias?` (conversa `35fcc925-...`; uma chamada a `vendas_indicadores`, 31 ms, `fim` 3,7 s depois do `conversa`):

> **Últimos 30 dias (01/11/2026 a 30/11/2026):** **Receita:** R$ 2.405.996,39. **Ticket médio:** cerca de R$ 1.053,86 (receita dividida por 2.283 pedidos realizados). Para comparação, no período anterior de 30 dias a receita foi de R$ 1.347.654,75 e o ticket médio foi de cerca de R$ 1.008,72 (1.336 pedidos). [...] A taxa de aprovação foi de 95,6%, contra 97,0% no período anterior.

A receita, os pedidos e a aprovação conferem com o painel no período **30 dias** (`receita` 2405996,39 e 1347654,75; `pedidos_realizados` 2283 e 1336; `taxa_de_aprovacao` 0,9558 e 0,9701). O ticket médio não é indicador do painel; é uma conta do modelo: 1.347.654,75 ÷ 1.336 = 1.008,72, certo; 2.405.996,39 ÷ 2.283 = 1.053,8749..., que arredonda para 1.053,87, e o modelo disse 1.053,86 (um centavo; na execução anterior, errou por R$ 0,14).

Diego (Diretoria) perguntou `O que está causando os atrasos?` (conversa `1ee07c43-...`): nenhuma chamada, nenhum dado, e a resposta "Ainda não tenho dados sobre atrasos para responder com segurança. Nesta conversa, nenhuma consulta foi feita [...]", pedindo o tipo de atraso, o período e o recorte, e "Se o painel tiver uma ferramenta para esse tipo de dado, eu consulto [...]. Se não tiver, eu digo que não tenho acesso a essas informações." A conversa lida depois tem `"rastreio": []` (na tela, "Nenhuma ferramenta foi consultada."). O histórico funciona para um perfil sem ferramentas.

Cada conversa foi pedida por quem não é o dono, com o token dele, nas quatro operações:

| Dono da conversa | Quem pediu | Na lista dele | Ler | Continuar | Apagar |
| --- | --- | --- | --- | --- | --- |
| `ana.vendas` | `vitor.vendas` (mesmo perfil) | Não aparece | 404 | 404 | 404 |
| `ana.vendas` | `diego.diretoria` (outro perfil) | Não aparece | 404 | 404 | 404 |
| `vitor.vendas` | `ana.vendas` (mesmo perfil) | Não aparece | 404 | 404 | 404 |
| `vitor.vendas` | `bruno.produtos` (outro perfil) | Não aparece | 404 | 404 | 404 |
| `diego.diretoria` | `ana.vendas` (outro perfil) | Não aparece | 404 | 404 | 404 |

Todas as recusas foram `{"erro":"Conversa não encontrada."}`, a mesma resposta de uma conversa que não existe (`GET /conversas/00000000-0000-4000-8000-000000000000` pela própria Ana) e de um identificador fora do formato, na leitura (`GET /conversas/nao-e-uuid`) e no corpo da pergunta (`POST /assistente` com `"id_da_conversa": "nao-e-uuid"`). Depois das tentativas, cada dono leu a própria conversa (200; a da Ana com os quatro itens): nenhuma foi apagada. O "continuar" foi recusado antes de o modelo ser chamado, sem evento nenhum e sem linha na auditoria. No fim, cada lista tinha só as conversas do dono: Ana, Vitor e Diego, uma cada; Bruno, que não perguntou, uma lista vazia. O banco `historico` tinha 3 conversas e 8 itens.

## 7. A pergunta acompanhada nos logs

Com o identificador do bloco de rastreio (no navegador) ou do evento `conversa` (no terminal):

bash:

```
docker compose logs api mcp | grep aeb93741-8dc3-4877-b14c-0f804d640a9d
```

PowerShell:

```
docker compose logs api mcp | Select-String aeb93741-8dc3-4877-b14c-0f804d640a9d
```

**Executado em 25/11/2026**, com o identificador da pergunta do passo 2:

```
api-1  | INFO:assistente:pergunta iniciada: pergunta aeb93741-8dc3-4877-b14c-0f804d640a9d, conversa 72b298e5-9b8f-4389-893b-07d4bff0f231, usuário 97bfb2e3-99f7-4091-aafd-10af557ea6d2
api-1  | INFO:assistente:pergunta terminada: pergunta aeb93741-8dc3-4877-b14c-0f804d640a9d, conversa 72b298e5-9b8f-4389-893b-07d4bff0f231, usuário 97bfb2e3-99f7-4091-aafd-10af557ea6d2
mcp-1  | INFO:consultas:consulta atrasos executada: 45 ms, pergunta aeb93741-8dc3-4877-b14c-0f804d640a9d
mcp-1  | INFO:servidor_mcp:chamada a 'vendas_atrasos': permitida, pergunta aeb93741-8dc3-4877-b14c-0f804d640a9d
mcp-1  | INFO:consultas:consulta atrasos executada: 49 ms, pergunta aeb93741-8dc3-4877-b14c-0f804d640a9d
mcp-1  | INFO:servidor_mcp:chamada a 'vendas_atrasos': permitida, pergunta aeb93741-8dc3-4877-b14c-0f804d640a9d
```

As três linhas: a da pergunta, na API (início e fim, com a conversa e o usuário); a de cada chamada, no servidor MCP (ferramenta e desfecho); a de cada consulta executada (nome e duração). O `docker compose logs` agrupa por serviço, por isso as linhas de um serviço vêm juntas, e não na ordem do relógio. A duração no rastreio (64 ms) é a da chamada vista pela API, com a rede e o servidor MCP; a da linha da consulta (45 e 49 ms), só a do banco. A pergunta do passo 3 (`7212f028-...`) deixou o mesmo desenho, com uma chamada só: as duas linhas da API, uma chamada e uma consulta de 36 ms.

O texto das perguntas não aparece no log: `docker compose logs api mcp | grep -c causando` deu 0, e o mesmo para "Compare as rotas", "qual dessas", "ticket", "90 dias" e "por lojista" (o texto das continuações recusadas no passo 6). As consultas das telas também têm linha, sem identificador:

```
api-1  | INFO:consultas:consulta indicadores executada: 33 ms, sem pergunta
```

A auditoria não ganhou o identificador da pergunta; continua só com o que o token prova.

## 8. A recarga preserva o histórico

```
docker compose exec postgres psql -U dono -d historico -tAc "select (select count(*) from historico.conversa), (select count(*) from historico.item)"
docker compose run --rm carga
```

E a contagem de novo.

**Executado em 25/11/2026**, depois dos passos 2, 3, 5 e 6: `3|8` antes (as conversas da Ana, do Vitor e do Diego; a do passo 5 já tinha sido apagada), a carga terminou com `carga: concluída`, e `3|8` depois. A conversa da Ana foi lida e continuada depois da recarga (passo 4). A recarga derruba e recria só o banco carregado; o `historico`, como a `auditoria`, fica.

## 9. As chamadas na auditoria

```
docker compose exec postgres psql -U dono -d auditoria -c "select to_char(horario,'HH24:MI:SS') h, nome_do_usuario, ferramenta, parametros, resultado from auditoria.chamada where horario > now() - interval '30 minutes' order by id"
```

**Executado em 25/11/2026**, depois dos passos 2 a 8 (sem o filtro de horário: o ambiente subiu do zero, e estas são todas as linhas da auditoria):

```
    h     | nome_do_usuario |     ferramenta     |         parametros         | resultado
----------+-----------------+--------------------+----------------------------+-----------
 15:44:31 | Ana Ribeiro     | vendas_atrasos     | {"agrupamento": "lojista"} | permitida
 15:44:31 | Ana Ribeiro     | vendas_atrasos     | {"agrupamento": "rota"}    | permitida
 15:44:42 | Ana Ribeiro     | vendas_atrasos     | {"agrupamento": "rota"}    | permitida
 15:44:58 | Ana Ribeiro     | vendas_indicadores | {"periodo": "90d"}         | permitida
 15:45:18 | Vitor Nunes     | vendas_indicadores | {"periodo": "30d"}         | permitida
```

As duas primeiras são do passo 2; a seguinte, do passo 3; a de 90 dias, da conversa apagada no passo 5, que continua na auditoria; a do Vitor, do passo 6, com o nome dele. Nas chamadas a `vendas_atrasos`, o modelo não passou o `periodo`, e valeu o padrão de 12 meses (o período que as respostas dizem). A pergunta do Diego, as continuações recusadas do passo 6 e a continuação do passo 4 não chamaram ferramenta, e não deixaram linha.

## Testes da entrega

Com o ambiente no ar e o limite alto no `mcp` (seção Testes do README), dentro de `backend/`, `uv run pytest`; no `frontend/`, `npm test`. O modelo real não aparece na suíte: a API é criada dentro do processo com um modelo roteirizado, e o resto é de verdade (Keycloak, serviço `mcp` do compose, bancos `auditoria` e `historico`).

| Arquivo | O que verifica |
| --- | --- |
| `test_conversa_gravada.py` | A pergunta sem conversa cria uma, e o evento `conversa` traz os identificadores; a conversa lida depois traz pergunta, resposta e situação; o título é o começo da primeira pergunta; a continuação chega ao modelo com os itens gravados, e a conversa reenviada no corpo recebe 400; perguntas simultâneas chegam ao modelo cada uma com a sua resposta; a resposta sem texto e a pergunta dela ficam fora; resposta com erro, com aviso de teto e parada pelo navegador ficam gravadas com a situação certa; 404 para conversa inexistente ou com identificador fora do formato, sem chamar o modelo; histórico fora do ar dá 503 sem chamar o modelo; a pergunta que não se grava não deixa conversa vazia, e a falha fica no log sem o texto dela; a falha ao gravar a resposta não muda o fluxo e fica no log |
| `test_isolamento_do_historico.py` | Listar, ler, continuar e apagar a conversa de outro usuário, do mesmo perfil (`ana.vendas` e `vitor.vendas`) e de outro, com a mesma recusa da inexistente; o mesmo `sub` com outro perfil não alcança as conversas do perfil antigo; sem token, token vencido e de outra aplicação recusados nas rotas do histórico; o CORS do `DELETE` só da origem do frontend (RF-18) |
| `test_lista_de_conversas.py` | A lista em ordem de última atividade, com título, e no teto de 50; vazia para quem nunca perguntou; apagar tira da lista e da leitura sem mexer na auditoria; apagar a inexistente ou duas vezes dá 404 |
| `test_rastreio.py` | O evento `chamada` com ferramenta, desfecho e duração; a chamada negada como `nao_concluida`, com o nome pedido; nenhum evento com parâmetro ou texto de erro; o rastreio de volta na leitura da conversa |
| `test_pergunta_nos_logs.py` | O mesmo identificador na linha da pergunta, na da chamada e na da consulta, sem o texto da pergunta; a consulta de uma rota das telas com linha sem identificador; o servidor MCP ignora um identificador fora do formato de UUID e atende sem ele (RNF-06) |
| `test_banco_do_historico.py` | A recarga preserva a conversa gravada; o papel do histórico não se conecta aos outros bancos; os papéis de perfil e o da auditoria não se conectam ao `historico` (ADR 0009) |

Do frontend, no Vitest: o estado da conversa (eventos `conversa` e `chamada`, carregar uma conversa do histórico, começar uma nova, o identificador enviado na pergunta seguinte), a lista de conversas (`listaDeConversas.test.ts`: carregando, carregada, vazia, erro, apagar, atualizar sem sumir), a leitura dos dois eventos novos (`fluxo.test.ts`), a tabela e o subtítulo em Markdown com HTML desligado (`TextoEmMarkdown.test.tsx`) e o painel (`PainelDoAssistente.test.tsx`: expandir só em tela larga, a lista ao lado no modo expandido, o bloco de rastreio, a sugestão em linha, o indicador de estado).

Requisitos cobertos:

| Requisito | Onde |
| --- | --- |
| RF-18 Histórico isolado por usuário | `test_isolamento_do_historico.py`, `test_lista_de_conversas.py`; passos 4 a 6 |
| RNF-06 Rastreio nos logs | `test_pergunta_nos_logs.py`; passo 7 |
| FE §8 Bloco de rastreio | `test_rastreio.py`, `PainelDoAssistente.test.tsx`; passo 2 (manual) |
| FE §8 Chat expandido | `PainelDoAssistente.test.tsx`, `TextoEmMarkdown.test.tsx`; passo 3 (manual) |
| ADR 0009 Histórico em banco próprio | `test_banco_do_historico.py`; passo 8 |

## Encerrar

```
docker compose down -v
```

Apaga também o histórico e a auditoria.
