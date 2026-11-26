# Roteiro de demonstração: entrega 9, perfil Comercial

Este roteiro mostra o que a 9 acrescenta: o perfil Comercial ganha o caminho inteiro que Vendas e Produtos já tinham (camada de leitura com o papel `comercial`, quatro rotas na API, quatro ferramentas no servidor MCP, painel e pergunta sugerida no assistente), e a matriz de isolamento passa a cruzar três perfis reais (CA-01, CA-02). O Comercial enxerga só a própria metade da história dos dados: Mídia paga é o canal que mais converte, e é também o canal dos lojistas que atrasam (padrão 5 dos dados); a camada de leitura do Comercial não traz nada que ligue um canal aos atrasos, e a pergunta sobre eles termina em "não tenho acesso". Os comandos rodam na raiz do projeto, salvo quando o passo indica `backend/`. Onde o PowerShell e o bash diferem, vale o que os roteiros da 5b e da 8 mostram.

Pré-requisitos: Docker com Docker Compose, [uv](https://docs.astral.sh/uv/), Node.js 24 (para o MCP Inspector), um navegador e uma chave da API da Anthropic (o provedor do modelo padrão).

**O que foi conferido e como.** Em 26/11/2026, todos os passos foram executados num ambiente subido do zero (`docker compose down -v` e `docker compose up -d --build --wait`, a partir do código da branch de integração da entrega), com o `mcp` no limite padrão de frequência (30 chamadas por usuário por minuto). Os passos 2 a 5 e o 7 foram executados pela API e pelo servidor MCP, com o modelo real (`anthropic:claude-haiku-5-5`, o padrão): o token de cada usuário veio do comando de token de demonstração, e a pergunta foi enviada em `POST /assistente`, como o painel faz. O passo 6 foi conferido no Chrome, pelo agente, com os números comparados aos das rotas. O roteiro da 8 foi executado na mesma subida (o resultado está em `entrega-8.md`). As respostas do modelo mudam a cada execução; o que este roteiro anota é o resultado observado e o que deve se repetir. O que não foi conferido está na seção "Lacunas".

## 1. Configurar e subir

```
cp backend/.env.example backend/.env
```

No `backend/.env`, preencha `ANTHROPIC_API_KEY` e troque as senhas. Esta entrega acrescenta uma variável. **Quem já tem um `backend/.env` de antes da 9 precisa acrescentá-la e refazer a carga** (`docker compose run --rm --build carga`), que cria o papel e a camada de leitura do Comercial:

| Variável | O que é |
| --- | --- |
| `SENHA_DO_PAPEL_COMERCIAL` | A senha do papel `comercial`, com que a API e o servidor MCP leem a camada de leitura do Comercial, e só ela (ADR 0002). Sem ela, o perfil Comercial é negado em toda consulta |

Suba do zero, com o `mcp` no limite padrão de frequência:

```
docker compose down -v
docker compose up -d --build --wait
```

**Executado em 26/11/2026:** todos os contêineres `healthy` e a carga `Exited (0)`, com `carga: concluída` no log. O banco `historico` com 0 conversas e a auditoria com 0 linhas; o `mcp` com `LIMITE_DE_CHAMADAS_POR_USUARIO` 30:

```
docker compose exec postgres psql -U dono -d historico -tAc "select count(*) from historico.conversa"
docker compose exec postgres psql -U dono -d auditoria -tAc "select count(*) from auditoria.chamada"
```

### Como perguntar pelo terminal

Como nos roteiros da 5b e da 8, emita o token da aplicação dentro de `backend/` (vale 5 minutos):

```
TOKEN=$(uv run python -m token_de_demonstracao carla.comercial pulso-web)
```

A pergunta, com o fluxo de eventos lido até o `fim`:

```
curl -sN -X POST http://localhost:8000/assistente -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"pergunta":"Qual canal traz os leads que mais convertem?"}'
```

As rotas do painel do Comercial, com o mesmo token. Todas recebem só o período; a rota dos leads não aceita canal nem etapa (os filtros existem só na ferramenta `comercial_leads`):

```
curl -s "http://localhost:8000/comercial/indicadores?periodo=12m" -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/comercial/funil?periodo=12m" -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/comercial/canais?periodo=12m" -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/comercial/leads?periodo=12m" -H "Authorization: Bearer $TOKEN"
```

**Executado em 26/11/2026**, com o token de `carla.comercial`, nos quatro períodos (todas 200). Os indicadores:

| Período | Leads (anterior) | Em negociação | Novos lojistas (anterior) | Conversão (anterior) | Dias até fechar | Principal canal (parcela) |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 30 dias | 67 (75) | 49 | 14 (12) | 20,9% (16,0%) | 33,1 | Orgânico (28,4%) |
| 90 dias | 197 (213) | 135 | 36 (31) | 18,3% (14,6%) | 41,5 | Orgânico (27,9%) |
| 12 meses | 746 (580) | 181 | 126 (94) | 16,9% (16,2%) | 44,2 | Mídia paga (29,8%) |
| 24 meses | 1.326 (sem anterior) | 181 | 220 (sem anterior) | 16,6% (sem anterior) | 44,3 | Mídia paga (29,3%) |

O funil (leads criados no período, na etapa atual de cada um):

| Período | Novo | Contatado | Qualificado | Proposta | Fechado | Perdido |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 dias | 49 | 0 | 0 | 0 | 4 | 14 |
| 90 dias | 76 | 38 | 21 | 0 | 17 | 45 |
| 12 meses | 76 | 38 | 40 | 27 | 110 | 455 |
| 24 meses | 76 | 38 | 40 | 27 | 214 | 931 |

As seis etapas só aparecem preenchidas em 12 e 24 meses: a etapa de um lead não fechado depende da idade dele. Por isso o funil é mostrado em 12 meses.

Os canais em 12 meses, na ordem em que a rota devolve (da maior conversão para a menor):

| Canal | Leads | Novos lojistas | Conversão | Dias até fechar |
| --- | ---: | ---: | ---: | ---: |
| Mídia paga | 222 | 57 | 25,7% (0,2568) | 45,98 |
| Indicação | 100 | 22 | 22,0% | 37,95 |
| Eventos | 80 | 13 | 16,3% (0,1625) | 47,46 |
| Prospecção ativa | 169 | 17 | 10,1% (0,1006) | 48,35 |
| Orgânico | 175 | 17 | 9,7% (0,0971) | 39,65 |

Em 30 dias as bases são pequenas e a ordem troca: Indicação 3 de 10 (30,0%), Mídia paga 4 de 16 (25,0%), Orgânico 4 de 19, Prospecção ativa 2 de 12, Eventos 1 de 10. Em 90 dias: Mídia paga 16 de 48 (33,3%), Indicação 5 de 28, Prospecção ativa 7 de 45, Eventos 3 de 21, Orgânico 5 de 55. Em 24 meses: Mídia paga 97 de 389 (24,9%), Indicação 32 de 158, Eventos 18 de 142, Orgânico 40 de 339, Prospecção ativa 33 de 298. A conversão é novos lojistas do período divididos pelos leads criados no mesmo período, uma razão entre dois movimentos, e não uma coorte: num período curto ela pode até passar de 100%.

A rota dos leads devolveu, nos quatro períodos, os mesmos 20 leads (do 1500, "Gonçalves Lopes Ltda.", de 30/11/2026, ao 1481, "Carvalho Ltda.", de 20/11/2026), todos em Novo ou Perdido e sem data de fechamento: os 20 leads mais recentes não têm nenhum Fechado.

## 2. A pergunta sugerida do Comercial

Com o token de `carla.comercial`, pergunte `Qual canal traz os leads que mais convertem?` (a pergunta sugerida do painel).

**O que se espera:** 200; o evento `conversa` primeiro; uma `chamada` a `comercial_canais`, `concluida`; o `fim`. A resposta traz os canais em ordem de conversão, com os leads e os novos lojistas de cada um, e cada número confere com `/comercial/canais` no mesmo período.

**Executado pela API (26/11/2026).** 200; o `conversa` primeiro; um `estado` e uma `chamada` (`comercial_canais`, `concluida`, 11 ms) 0,7 s depois; 59 trechos de texto e o `fim` 2,8 s depois do `conversa`. A resposta:

> O canal que mais converte é a **Mídia paga**, nos últimos 12 meses (01/12/2025 a 30/11/2026).
>
> | Canal | Leads | Novos lojistas | Conversão | Dias até fechar |
> |---|---|---|---|---|
> | Mídia paga | 222 | 57 | 25,7% | 46,0 |
> | Indicação | 100 | 22 | 22,0% | 38,0 |
> | Eventos | 80 | 13 | 16,3% | 47,5 |
> | Prospecção ativa | 169 | 17 | 10,1% | 48,4 |
> | Orgânico | 175 | 17 | 9,7% | 39,6 |
>
> A Mídia paga também é o canal com mais leads e mais novos lojistas. A Indicação vem em seguida, com o ciclo mais curto (38 dias) e uma conversão próxima.
>
> A conversão aqui é novos lojistas do período dividido pelos leads criados no mesmo período. Não é a parcela exata dos leads desse período que fecharam.

**Os números conferem com a rota.** As cinco linhas são as de `/comercial/canais?periodo=12m` do passo 1, na mesma ordem, com as mesmas contagens; as conversões e os dias são os da rota, arredondados para uma casa (0,2568 → 25,7%; 45,98 → 46,0; 37,95 → 38,0; 47,46 → 47,5; 48,35 → 48,4; 39,65 → 39,6). O período dito é o da rota (2025-12-01 a 2026-11-30). As duas frases de leitura também conferem: Mídia paga tem mais leads (222) e mais novos lojistas (57), e Indicação tem o menor tempo até fechar. O modelo não refez a conta da conversão e repetiu a ressalva da descrição da ferramenta (razão entre dois movimentos, não coorte).

## 3. Outras perguntas do Comercial

Cada uma numa conversa nova, com o token de `carla.comercial`.

**Executado pela API (26/11/2026):**

- `Quantos leads estão em cada etapa do funil nos últimos 12 meses?`: uma chamada a `comercial_funil` (9 ms), `fim` em 3,1 s. A resposta trouxe a tabela Novo 76, Contatado 38, Qualificado 40, Proposta 27, Fechado 110, Perdido 455, igual à rota, e "Cada lead aparece só na etapa em que está hoje, então os números não são acumulados. Dos 746 leads criados no período, 455 foram perdidos e 110 viraram lojistas. Os outros 181 ainda estão em negociação." (746 e 181 conferem com os indicadores).
- `Quais leads de Indicação estão em Proposta?`: uma chamada a `comercial_leads` com `canal` "Indicação" e `etapa` "Proposta" (8 ms), `fim` em 1,8 s. A resposta: "Não encontrei leads de **Indicação** em **Proposta** nos últimos 12 meses (de 01/12/2025 a 30/11/2026)." Confere: nos dados não há nenhum lead de Indicação em Proposta (0, contado pelo dono na camada de leitura). O recorte sem leads dá lista vazia, e o modelo não inventou.
- `Quais leads de Mídia paga estão em Proposta?`: uma chamada a `comercial_leads` com `canal` "Mídia paga" e `etapa` "Proposta" (10 ms), `fim` em 2,8 s. A resposta listou 8 leads, do mais novo para o mais antigo (1287 Rocha Pastor S.A., 28/08/2026; 1276 Pastor Montenegro S/A; 1270 Cirino Gomes S/A; 1265 da Cruz da Luz Ltda.; 1260 Costa S/A; 1256 Peixoto Siqueira S.A.; 1227 Barbosa Carvalho S/A; 1226 Aragão Garcia e Filhos, 03/08/2026) e disse que nenhum tem data de fechamento. Confere linha a linha com a camada de leitura lida pelo dono (8 linhas, mesmos identificadores, empresas e datas).

Nas duas chamadas a `comercial_leads` o modelo não passou o `periodo`, e valeu o padrão de 12 meses, que é o período que as respostas dizem.

## 4. A pergunta sobre os atrasos (RF-17)

Com o token de `carla.comercial`, numa conversa nova: `os lojistas de Mídia paga atrasam mais?`

**O que se espera:** o assistente diz que não tem acesso a esse dado, sem inventar número; o rastreio só com ferramentas do Comercial (ou nenhuma); a auditoria sem chamada fora das ferramentas do Comercial. A garantia não depende do modelo: o assistente só recebe as quatro ferramentas do Comercial, com o token da Carla; o papel `comercial` só lê a camada do Comercial; e essa camada não tem o identificador do lojista, pedido, entrega nem atraso.

**Executado pela API (26/11/2026).** 200; uma chamada a `comercial_canais` (`concluida`, 10 ms); 67 trechos e `fim` 3,8 s depois do `conversa`. A resposta:

> Não tenho dados sobre atraso de pagamento dos lojistas, então não consigo responder se os de Mídia paga atrasam mais.
>
> O que consigo mostrar é o tempo que os leads de cada canal levam para fechar, nos últimos 12 meses. Isso mede a velocidade da venda, não o pagamento.
>
> [a mesma tabela dos cinco canais do passo 2]
>
> Mídia paga tem a maior conversão e um tempo até fechar na média dos canais. Para saber sobre pagamentos, seria preciso uma fonte financeira ou de cobrança, que não tenho acesso.

A pergunta terminou em "não tenho acesso", sem número de atraso, e a tabela mostrada é a do Comercial, com os números da rota. Um deslize de interpretação: o modelo leu "atrasam" como atraso de pagamento; nos dados, o atraso é o da entrega dos pedidos. A conclusão (não tem o dado) é a mesma nos dois sentidos.

A pergunta refeita sem ambiguidade, `Os lojistas que vieram de Mídia paga atrasam mais as entregas dos pedidos? Qual a receita deles?`: uma chamada a `comercial_canais` (10 ms), `fim` em 4,4 s, e a resposta abriu com "Não tenho acesso a dados de entregas nem de receita, então não consigo dizer se os lojistas de Mídia paga atrasam mais as entregas nem qual é a receita deles.", seguida dos números de captação de Mídia paga (222 leads, 57 novos lojistas, 25,7%, 46 dias) e da tabela dos canais, e fechou com "Para saber sobre entregas e receita, você precisará de uma fonte de pedidos e faturamento, que não está entre as ferramentas que tenho."

**A auditoria.** Todas as linhas das perguntas da Carla nos passos 2 a 4 (os horários da auditoria estão em UTC):

```
docker compose exec postgres psql -U dono -d auditoria -c "select id, to_char(horario,'HH24:MI:SS') h, nome_do_usuario, perfil, ferramenta, parametros, resultado from auditoria.chamada order by id"
```

```
 id |    h     | nome_do_usuario |  perfil   |    ferramenta    |                  parametros                  | resultado
----+----------+-----------------+-----------+------------------+----------------------------------------------+-----------
 48 | 11:40:36 | Carla Mendes    | comercial | comercial_canais | {"periodo": "12m"}                           | permitida
 49 | 11:40:44 | Carla Mendes    | comercial | comercial_canais | {"periodo": "12m"}                           | permitida
 50 | 11:41:04 | Carla Mendes    | comercial | comercial_funil  | {"periodo": "12m"}                           | permitida
 51 | 11:41:12 | Carla Mendes    | comercial | comercial_leads  | {"canal": "Indicação", "etapa": "Proposta"}  | permitida
 52 | 11:41:19 | Carla Mendes    | comercial | comercial_leads  | {"canal": "Mídia paga", "etapa": "Proposta"} | permitida
 53 | 11:41:28 | Carla Mendes    | comercial | comercial_canais | {"periodo": "12m"}                           | permitida
```

A linha 48 é a pergunta sugerida; a 49, a pergunta sobre os atrasos; a 53, a pergunta refeita. Nenhuma chamada fora das ferramentas do Comercial, e nenhuma tentativa negada: diante das perguntas sobre atrasos, o modelo não pediu ferramenta de Vendas. As linhas 1 a 47 são do roteiro da 8 e da matriz do passo 5, executados antes.

**No sentido contrário**, com o token de cada um, numa conversa nova:

- `ana.vendas`, `Qual canal traz os leads que mais convertem?`: nenhuma chamada, `fim` em 2,7 s, e "Não tenho acesso a dados de **leads** nem de **canais de origem** (como anúncios, redes sociais ou e-mail), então não consigo dizer qual canal converte mais.", seguida do que o painel de Vendas oferece.
- `bruno.produtos`, `Quantos leads estão em cada etapa do funil?`: nenhuma chamada, `fim` em 1,6 s, e "Não tenho acesso a dados de leads nem de etapas do funil. As ferramentas que recebi cobrem só produtos [...]".

Nenhuma das duas deixou linha na auditoria.

## 5. A matriz entre `ana.vendas`, `bruno.produtos` e `carla.comercial` (CA-01, CA-02)

**Rotas.** Com o token de cada um, as treze rotas de dados (as quatro de Vendas, as cinco de Produtos e as quatro do Comercial), com `?periodo=12m` e com um período inválido (`?periodo=xyz`).

**Executado em 26/11/2026:**

| Quem pediu | Rotas de Vendas (4) | Rotas de Produtos (5) | Rotas do Comercial (4) |
| --- | --- | --- | --- |
| `ana.vendas` | 200 | 403 | 403 |
| `bruno.produtos` | 403 | 200 | 403 |
| `carla.comercial` | 403 | 403 | 200 |

Os 26 pedidos negados receberam `403 {"erro":"Acesso negado."}`, a mesma negação em toda rota. Com o período inválido, o dono recebeu `400 {"erro":"Parâmetro inválido."}`, e os outros dois o mesmo `403`: a negação vem antes da validação do parâmetro e não diz se o dado existe.

**Ferramentas.** Com o token do cliente `pulso-inspector` de cada um (`uv run python -m token_de_demonstracao <usuário> pulso-inspector`), a lista pelo Inspector, como no roteiro da 4a:

```
npx @modelcontextprotocol/inspector@2.16.0 --cli http://localhost:8001/mcp --transport http --stored-auth-only --header "Authorization: Bearer $TOKEN" --method tools/list
```

**Executado em 26/11/2026**, pelo Inspector (Node.js 24.20) e, de novo, com `tools/list` cru por `curl`, com o mesmo resultado: `ana.vendas` lista só as cinco `vendas_*`; `bruno.produtos`, só as cinco `produtos_*`; `carla.comercial`, só `comercial_indicadores`, `comercial_funil`, `comercial_canais` e `comercial_leads`.

A chamada direta de cada uma das catorze ferramentas, crua, com o token de cada um:

```
curl -s -X POST http://localhost:8001/mcp -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vendas_indicadores","arguments":{"periodo":"12m"}}}'
```

| Quem chamou | `vendas_*` (5) | `produtos_*` (5) | `comercial_*` (4) |
| --- | --- | --- | --- |
| `ana.vendas` | resultado (4) e parâmetro inválido (1) | Ferramenta desconhecida. | Ferramenta desconhecida. |
| `bruno.produtos` | Ferramenta desconhecida. | resultado | Ferramenta desconhecida. |
| `carla.comercial` | Ferramenta desconhecida. | Ferramenta desconhecida. | resultado |

A ferramenta de outro perfil recebeu sempre `{"content":[{"text":"Ferramenta desconhecida.","type":"text"}],"isError":true}`, igual, letra por letra, à resposta de uma ferramenta que não existe (`nao_existe`, chamada pelos três). O "parâmetro inválido" da Ana é de `vendas_atrasos`, chamada só com o `periodo`, sem o `agrupamento` obrigatório: é a recusa do dono, não a de outro perfil. Na auditoria, as chamadas ficaram com o nome e o perfil de quem chamou: Ana Ribeiro, 4 `permitida`, 1 `parametro_invalido` e 10 `negada` (as nove de outro perfil e a inexistente); Bruno Costa, 5 `permitida` e 10 `negada`; Carla Mendes, 4 `permitida` e 11 `negada`.

**Papéis do banco.** Conecte com cada papel (a senha é a do `backend/.env`):

```
docker compose exec postgres psql -h 127.0.0.1 -U comercial -d marketplace
```

**Executado em 26/11/2026:**

| Papel | Comando | Resultado |
| --- | --- | --- |
| `comercial` | `select count(*) from comercial.lead;` | `1500` |
| `comercial` | `select * from vendas.pedido limit 1;` | `ERROR:  permission denied for schema vendas` |
| `comercial` | `select * from produtos.produto limit 1;` | `ERROR:  permission denied for schema produtos` |
| `comercial` | `select * from dados_de_origem.lead limit 1;` | `ERROR:  permission denied for schema dados_de_origem` |
| `comercial` | `select * from dados_de_origem.lojista limit 1;` | `ERROR:  permission denied for schema dados_de_origem` |
| `comercial` | `create temporary table t (id int);` | `ERROR:  cannot execute CREATE TABLE in a read-only transaction` |
| `comercial` | conectar aos bancos `auditoria` e `historico` | `FATAL:  permission denied for database` (sem o privilégio `CONNECT`), nos dois |
| `vendas` | `select * from comercial.lead limit 1;` | `ERROR:  permission denied for schema comercial` |
| `produtos` | `select * from comercial.lead limit 1;` | `ERROR:  permission denied for schema comercial` |

A camada de leitura do Comercial, lida pelo dono em `information_schema.columns`, tem duas views e sete colunas: `lead` (`id`, `empresa`, `canal`, `etapa`, `data_criacao`, `data_fechamento`) e `referencia` (`data_referencia`). Não há e-mail de contato, identificador do lojista, CNPJ, cidade, UF, pedido, entrega, atraso, receita, produto nem avaliação (RF-05): nada nela liga um canal aos atrasos.

## 6. Conferência no navegador

Abra `http://localhost:5173` e entre como `carla.comercial`. Confira, comparando com as rotas do passo 1 no mesmo período.

**Conferido no Chrome em 26/11/2026**, pelo agente, numa janela de 1.568 px de largura:

- **Entrada:** depois do login, a página "Painel Comercial", com "Olá, Carla.", o nome "Carla Mendes" e o perfil "Comercial" na barra lateral e no topo, com o marcador do perfil em tom terroso. Não aparece "O painel chega em breve".
- **Cartões, em 12 meses:** **Leads** 746, +28,6%, "181 em negociação"; **Novos lojistas** 126, +34,0%, "44 dias até fechar, em média"; **Conversão** 16,9%, +0,7 p.p., "Novos lojistas por leads do período"; **Principal canal** "Mídia paga", "29,8% dos leads do período", sem variação. Conferem com `/comercial/indicadores` (746 ÷ 580 = +28,6%; 126 ÷ 94 = +34,0%; 16,89% − 16,21% = +0,7 p.p.; 0,2976). As três variações aparecem em verde, com seta para cima.
- **Gráfico "Leads por etapa do funil", em 12 meses:** barras na ordem Novo 76, Contatado 38, Qualificado 40, Proposta 27, Fechado 110 e, em cinza, separado na legenda ("Etapas do funil" e "Perdido"), Perdido 455. Iguais aos de `/comercial/funil`. A dica da barra mostra a etapa e os leads ("Perdido, Leads 455").
- **Gráfico "Novos lojistas por canal", em 12 meses:** Mídia paga 57, Indicação 22, Orgânico 17, Prospecção ativa 17, Eventos 13. A dica da barra de Mídia paga mostra "Novos lojistas 57, Conversão 25,7%, Leads do período 222". Iguais aos de `/comercial/canais`.
- **Tabela "Desempenho dos canais":** as cinco linhas da tabela do passo 1, na mesma ordem (Mídia paga 222, 57, 25,7%, 46; Indicação 100, 22, 22,0%, 38; Eventos 80, 13, 16,3%, 47; Prospecção ativa 169, 17, 10,1%, 48; Orgânico 175, 17, 9,7%, 40), com os dias arredondados para inteiro.
- **Tabela "Leads recentes":** 20 linhas, de "Gonçalves Lopes Ltda." (Orgânico, Novo, 30/11/2026) a "Carvalho Ltda." (Eventos, Novo, 20/11/2026), com as colunas Empresa, Canal, Etapa, Criação e Fechamento; o fechamento aparece como "—" nas vinte. As mesmas empresas, canais, etapas e datas de `/comercial/leads`.
- **"Canal" em toda a tela:** os títulos, as legendas e as colunas dizem "canal"; a palavra "origem" não aparece no painel.
- **Troca de período:** todos os blocos acompanham, e o período fica no endereço (`?periodo=90d`, `?periodo=12m`). Em 30 dias: 67 (−10,7%, em vermelho), 49 em negociação; 14 (+16,7%), 33 dias; 20,9% (+4,9 p.p.); Orgânico, 28,4%; funil 49, 0, 0, 0, 4 e 14; novos lojistas por canal 4, 4, 3, 2 e 1. Em 90 dias: 197 (−7,5%), 135; 36 (+16,1%), 42 dias; 18,3% (+3,7 p.p.); Orgânico, 27,9%; funil 76, 38, 21, 0, 17 e 45. Em 24 meses: 1.326, 220, 16,6% e Mídia paga com 29,3%, os quatro cartões sem variação; funil 76, 38, 40, 27, 214 e 931; novos lojistas por canal 97, 40, 33, 32 e 18. Tudo igual às rotas do passo 1.
- **Assistente:** o painel lateral "Assistente PULSO, Perfil Comercial" com a pergunta sugerida "Qual canal traz os leads que mais convertem?". Clicada, a resposta chegou com a mesma tabela do passo 2 (222, 57, 25,7%, 46,0 em Mídia paga, e assim por diante). No modo expandido, a lista de conversas mostrou as sete conversas da Carla (as seis dos passos 2 a 4 e esta), e o bloco "Como esta resposta foi obtida", aberto, mostrou `comercial_canais`, "concluída", 9 ms e o identificador da pergunta. De volta ao painel lateral, a tabela larga rola na horizontal sem alargar o painel. A chamada ficou na auditoria (linha 54, Carla Mendes, `comercial_canais`, `permitida`).
- **Troca de usuário:** depois de **Sair**, a entrada como `ana.vendas` mostrou o "Painel de Vendas" ("Olá, Ana."; 16.795 pedidos, R$ 17.082.039,33, taxa de atraso de 9,0% com 1.411 atrasos, aprovação de 96,0%; entregas 436, 57, 14.211 e 1.411, iguais às rotas de Vendas em 12 meses) e a pergunta sugerida "O que está causando os atrasos?". Depois de sair de novo, a entrada como `bruno.produtos` mostrou o "Painel de Produtos" (2.000 produtos no catálogo, nota média 4,09, 20 produtos mal avaliados, 11.594 avaliações) e a pergunta sugerida "Quais categorias concentram as piores notas?". Três usuários, três painéis diferentes, cada um com a própria pergunta sugerida (CA-01). Na primeira tentativa de entrar como `ana.vendas`, a tela de login respondeu "Usuário ou senha inválidos."; a segunda tentativa, com a mesma senha colada de novo, entrou. A causa provável é a colagem da senha pelo agente, não o ambiente; não se repetiu com `bruno.produtos`.

## 7. O tempo das rotas (RNF-05)

Dentro de `backend/`:

```
uv run python tests/demonstracao.py tempos 24m comercial
```

O comando faz o login como o usuário do perfil, aquece cada rota do perfil (lidas do registro da API) com um pedido e mede cinco pedidos por rota, no período de 24 meses.

**Executado em 26/11/2026**, para os três perfis, contra a API do compose:

| Rota | Mediana | Máximo |
| --- | ---: | ---: |
| `/comercial/indicadores` | 3 ms | 4 ms |
| `/comercial/funil` | 3 ms | 3 ms |
| `/comercial/canais` | 3 ms | 3 ms |
| `/comercial/leads` | 3 ms | 3 ms |
| `/produtos/indicadores` | 13 ms | 14 ms |
| `/produtos/notas` | 6 ms | 7 ms |
| `/produtos/categorias` | 16 ms | 16 ms |
| `/produtos/mal-avaliados` | 7 ms | 8 ms |
| `/produtos/avaliacoes` | 11 ms | 11 ms |
| `/vendas/indicadores` | 45 ms | 47 ms |
| `/vendas/evolucao` | 65 ms | 66 ms |
| `/vendas/situacao-das-entregas` | 35 ms | 37 ms |
| `/vendas/pedidos-recentes` | 4 ms | 4 ms |

Todas muito abaixo da meta de 3 s. Além do comando, a suíte agora mede todas as rotas de dados do registro em 24 meses contra a meta (`test_tempo_das_rotas.py`), no lugar do teste que media só as de Vendas.

## Lacunas

O que este roteiro **não** conferiu:

1. **Tela pequena.** O painel do Comercial no celular, com as tabelas rolando na horizontal, não foi conferido: a conferência foi numa janela larga só.
2. **Teclado e leitor de tela.** O foco e os rótulos dos gráficos e das tabelas do Comercial não foram conferidos no navegador; só os testes do Vitest os cobrem.
3. **Estados de carregamento, vazio e erro** dos blocos não foram provocados no navegador; só os testes do Vitest os cobrem.
4. **Diretoria.** A entrada como `diego.diretoria`, que deve continuar em "O painel chega em breve", não foi conferida no navegador nesta execução.
5. **O tom exato do terracota** (`#B47B58`) não foi medido; o que se viu foi o marcador do perfil em tom terroso.
6. **O limite de frequência com a Carla** não foi provocado à mão; é genérico por usuário e está nos testes (`test_limite_de_frequencia.py`).
7. **A chamada negada com o modelo real** continua sem ser vista: diante das perguntas sobre atrasos, o modelo não tentou ferramenta de outro perfil, então o rastreio não mostrou nenhuma chamada "não concluída". A negação foi vista só na chamada direta do passo 5 e nos testes, com o modelo roteirizado.
8. **Claude e ChatGPT** com o perfil Comercial ficam para a entrega 7.

## Testes da entrega

Com o ambiente no ar e o limite alto no `mcp` (seção Testes do README), dentro de `backend/`, `uv run pytest`; no `frontend/`, `npm test`, `npm run typecheck`, `npm run lint` e `npm run build`. O modelo real não aparece na suíte.

Os testes da entrega: `test_camada_comercial.py`, `test_indicadores_do_comercial.py`, `test_funil_do_comercial.py`, `test_canais_do_comercial.py`, `test_leads_do_comercial.py` e `test_tempo_das_rotas.py`, além das matrizes, que crescem pelos registros (`test_matriz_de_papeis.py`, `test_matriz_de_isolamento.py`, `test_isolamento_do_assistente.py` e `test_registro_de_ferramentas.py`). No Vitest: os validadores e os blocos do painel do Comercial (`frontend/src/comercial/`) e a pergunta sugerida do Comercial.

O resultado da suíte completa, executada uma vez no fechamento desta entrega, está na situação da 9 em `docs/ROADMAP.md`.

## Encerrar

```
docker compose down -v
```

Apaga também o histórico e a auditoria.
