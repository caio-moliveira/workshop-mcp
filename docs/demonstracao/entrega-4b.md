# Roteiro de demonstração: entrega 4b, auditoria e limite de frequência

Este roteiro mostra a entrega 4b pelo terminal: toda chamada ao servidor MCP vira uma linha na auditoria, com usuário, perfil, ferramenta, parâmetros, resultado e horário; quem passa de 30 chamadas por minuto é barrado; a recarga preserva a auditoria; e o papel de Vendas não consegue lê-la. Cada passo traz o comando e o resultado esperado com a configuração padrão. Os comandos rodam na raiz do projeto, salvo quando o passo indica `backend/`. Onde o PowerShell e o bash diferem, o passo mostra os dois.

Pré-requisitos: Docker com Docker Compose e [uv](https://docs.astral.sh/uv/). O MCP Inspector não é necessário: as chamadas saem como no fim do passo 5 do roteiro da 4a, com o JSON-RPC cru, para que cada resposta e cada linha da auditoria possam ser conferidas no terminal.

**O que foi conferido e como.** Os resultados abaixo foram observados no ambiente local em 24/11/2026, nos dois terminais: as linhas dos passos 3 a 5, a barreira na 31ª chamada, a auditoria intacta depois da recarga e as recusas do passo 7. Os horários mudam a cada execução; os demais valores, não.

## 1. Preparar a configuração e subir

```
cp backend/.env.example backend/.env
docker compose down -v
docker compose up -d --build --wait
```

O `backend/.env` ganhou uma variável nesta entrega: `SENHA_DO_PAPEL_AUDITORIA`, a senha do papel `auditoria`, com que o servidor MCP grava as chamadas. Quem já tem um `.env` de antes precisa acrescentá-la; sem ela a carga falha.

A primeira carga cria, além do banco `marketplace`, o banco `auditoria`, o papel `auditoria` e a tabela `auditoria.chamada`, sem passo manual (ADR 0008).

**O limite da demonstração.** O limite de frequência vem de duas variáveis do shell, `LIMITE_DE_CHAMADAS_POR_USUARIO` e `JANELA_DO_LIMITE_EM_SEGUNDOS`, com padrão de 30 chamadas por 60 segundos. O roteiro usa o padrão. Se o ambiente estiver com o limite alto da suíte de testes (seção Testes do README), suba o `mcp` de novo sem a variável:

```
docker compose up -d --wait mcp
```

Confira o limite em vigor:

```
docker compose exec mcp env
```

Esperado, entre as outras variáveis: `LIMITE_DE_CHAMADAS_POR_USUARIO=30` e `JANELA_DO_LIMITE_EM_SEGUNDOS=60`.

## 2. Como consultar a auditoria

A auditoria é lida com o papel dono, o único que lê o banco `auditoria`. Nenhuma ferramenta do servidor MCP a lê (RF-32); o painel é da entrega 11. Cada passo abaixo usa uma variação desta consulta:

```
docker compose exec postgres psql -U dono -d auditoria -c "select horario, nome_do_usuario, perfil, ferramenta, parametros, resultado from auditoria.chamada order by id desc limit 5"
```

A tabela tem uma linha por chamada, com o desfecho final:

| Coluna | O que guarda |
| --- | --- |
| `horario` | A chegada da chamada, com fuso. O `psql` do contêiner mostra em UTC (`+00`). |
| `id_do_usuario` | O `sub` do token: é por ele que o usuário é identificado e que o limite conta. Os usuários de demonstração têm identificador fixo no realm: o mesmo usuário tem o mesmo `sub` a cada subida do Keycloak. |
| `nome_do_usuario` | O nome que veio no token, como `Ana Ribeiro`, e não o login `ana.vendas`. |
| `perfil` | O perfil do token já validado, nunca algo enviado pelo assistente (RS-03). |
| `ferramenta` | O nome pedido, como chegou, mesmo que não exista (cortado acima de 200 caracteres). |
| `parametros` | Os argumentos como chegaram, em JSON (cortados acima de 4 KB). |
| `parametros_cortados` | Se os argumentos foram cortados. |
| `resultado` | `permitida`, `negada`, `parametro_invalido`, `limitada` ou `falha`. |

Listar as ferramentas não gera linha, e um token recusado (401) também não: não há usuário conhecido.

## 3. Uma chamada permitida de Vendas

Dentro de `backend/`, emita o token de `ana.vendas` pelo cliente do Inspector, como no passo 4 do roteiro da 4a. Ele vale 5 minutos:

```
uv sync --locked
```

PowerShell:

```
$TOKEN = uv run python -m token_de_demonstracao ana.vendas pulso-inspector
```

bash:

```
TOKEN=$(uv run python -m token_de_demonstracao ana.vendas pulso-inspector)
```

Chame `vendas_indicadores` com o período de 30 dias.

bash:

```
curl -s -X POST http://localhost:8001/mcp -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vendas_indicadores","arguments":{"periodo":"30d"}}}'
```

PowerShell:

```
$corpo = '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vendas_indicadores","arguments":{"periodo":"30d"}}}'
Invoke-RestMethod -Method Post http://localhost:8001/mcp -Headers @{Authorization="Bearer $TOKEN"; Accept="application/json, text/event-stream"} -ContentType "application/json" -Body $corpo | ConvertTo-Json -Depth 5
```

Esperado: os indicadores de `2026-11-01` a `2026-11-30` (2283 pedidos realizados, anterior 1336), com `"isError":false`. Na raiz do projeto, a linha da chamada, no formato expandido do `psql` (`-x`):

```
docker compose exec postgres psql -U dono -d auditoria -x -c "select horario, id_do_usuario, nome_do_usuario, perfil, ferramenta, parametros, parametros_cortados, resultado from auditoria.chamada order by id desc limit 1"
```

```
-[ RECORD 1 ]-------+-------------------------------------
horario             | 2026-11-24 21:24:37.599351+00
id_do_usuario       | 97bfb2e3-99f7-4091-aafd-10af557ea6d2
nome_do_usuario     | Ana Ribeiro
perfil              | vendas
ferramenta          | vendas_indicadores
parametros          | {"periodo": "30d"}
parametros_cortados | f
resultado           | permitida
```

A linha já está no banco quando a resposta chega: o servidor MCP grava antes de responder, e recusa a chamada se não conseguir gravar (ADR 0008).

## 4. Uma chamada negada da Diretoria

Dentro de `backend/`, emita o token de `diego.diretoria` como no passo 3 (`... token_de_demonstracao diego.diretoria pulso-inspector`) e repita a chamada de `vendas_indicadores`, agora sem argumentos (`"arguments":{}`).

Esperado, como na 4a:

```
{"jsonrpc":"2.0","id":1,"result":{"content":[{"text":"Ferramenta desconhecida.","type":"text"}],"isError":true}}
```

Na auditoria, as duas últimas linhas:

```
docker compose exec postgres psql -U dono -d auditoria -c "select horario, nome_do_usuario, perfil, ferramenta, parametros, resultado from auditoria.chamada order by id desc limit 2"
```

```
            horario            | nome_do_usuario |  perfil   |     ferramenta     |     parametros     | resultado
-------------------------------+-----------------+-----------+--------------------+--------------------+-----------
 2026-11-24 21:25:03.824025+00 | Diego Almeida   | diretoria | vendas_indicadores | {}                 | negada
 2026-11-24 21:24:37.599351+00 | Ana Ribeiro     | vendas    | vendas_indicadores | {"periodo": "30d"} | permitida
(2 rows)
```

A resposta não diz ao Diego que a ferramenta existe (RS-08), mas a auditoria guarda o nome que ele pediu (RF-31). Uma ferramenta inexistente, como `nao_existe`, também fica como `negada`, com o nome pedido; o motivo detalhado fica só no log do serviço (`docker compose logs mcp`): `perfil diretoria pediu uma ferramenta de outro perfil ou inexistente: 'vendas_indicadores'`.

## 5. Uma chamada barrada pelo limite

**Faça este passo pelo menos um minuto depois da chamada da Ana no passo 3.** O limite conta as chamadas de cada usuário no último minuto; se a do passo 3 ainda estiver dentro da janela, a barreira vem uma chamada antes.

Dentro de `backend/`, emita de novo o token de `ana.vendas` (passo 3) e faça 31 chamadas seguidas de `vendas_situacao_das_entregas`. Cada linha mostra o número da chamada e se ela voltou como erro.

bash:

```
for i in $(seq 31); do echo "$i $(curl -s -X POST http://localhost:8001/mcp -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vendas_situacao_das_entregas","arguments":{}}}' | grep -o '"isError":[a-z]*')"; done
```

PowerShell:

```
$corpo = '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vendas_situacao_das_entregas","arguments":{}}}'
1..31 | ForEach-Object { $resposta = Invoke-RestMethod -Method Post http://localhost:8001/mcp -Headers @{Authorization="Bearer $TOKEN"; Accept="application/json, text/event-stream"} -ContentType "application/json" -Body $corpo; "$_ $($resposta.result.isError)" }
```

Esperado: as 30 primeiras passam (`"isError":false`, ou `False` no PowerShell) e a 31ª é barrada (`"isError":true`, ou `True`). Mais uma chamada, como no passo 3, mostra a mensagem da barreira:

```
{"jsonrpc":"2.0","id":1,"result":{"content":[{"text":"Muitas chamadas em pouco tempo. Tente de novo em instantes.","type":"text"}],"isError":true}}
```

É um erro de ferramenta, não um HTTP 429: o assistente explica ao usuário o que houve, em vez de tratar como queda do servidor. O log do serviço registra `usuário <id do usuário> passou do limite de frequência`.

**Outro usuário não é afetado.** Logo em seguida, repita a chamada do Diego (passo 4): a resposta continua `Ferramenta desconhecida.`, e a linha dele é `negada`, não `limitada`.

Na auditoria, logo depois, as chamadas do último minuto, por usuário e resultado:

```
docker compose exec postgres psql -U dono -d auditoria -c "select nome_do_usuario, resultado, count(*) from auditoria.chamada where horario > now() - interval '1 minute' group by nome_do_usuario, resultado order by 1, 2"
```

```
 nome_do_usuario | resultado | count
-----------------+-----------+-------
 Ana Ribeiro     | limitada  |     2
 Ana Ribeiro     | permitida |    30
 Diego Almeida   | negada    |     1
(3 rows)
```

As duas `limitada` são a 31ª chamada do laço e a da mensagem. A chamada barrada não conta para o limite: passado um minuto da primeira chamada do laço, a Ana volta a ser atendida, sem reiniciar o servidor. As negadas e as com parâmetro inválido contam, para conter quem sonda o servidor.

## 6. A recarga preserva a auditoria

Conte as linhas antes:

```
docker compose exec postgres psql -U dono -d auditoria -c "select count(*), max(horario) from auditoria.chamada"
```

Recarregue o banco carregado, com o resto no ar:

```
docker compose run --rm --build carga
```

A carga mostra `carga: recriando o banco marketplace` e termina com `carga: concluída`. Conte de novo: o número de linhas e o horário da última são os mesmos de antes. A recarga derruba e recria só o banco `marketplace` (ADR 0001); o banco `auditoria` vive à parte e a carga nunca o derruba, só cria o que falta e reaplica a senha do papel `auditoria` (ADR 0008). As linhas dos passos 3 a 5 continuam lá:

```
docker compose exec postgres psql -U dono -d auditoria -c "select horario, nome_do_usuario, perfil, ferramenta, parametros, resultado from auditoria.chamada where resultado in ('permitida', 'negada') order by id desc limit 2"
```

O servidor MCP continua atendendo depois da recarga: uma nova chamada da Ana passa e vira mais uma linha.

O que apaga a auditoria é `docker compose down -v`: o Postgres não tem volume.

## 7. Vendas não lê a auditoria

Conecte ao banco da auditoria com o papel de Vendas. A senha é o valor de `SENHA_DO_PAPEL_VENDAS` em `backend/.env`:

```
docker compose exec postgres psql -h 127.0.0.1 -U vendas -d auditoria
```

```
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  permission denied for database "auditoria"
DETAIL:  User does not have CONNECT privilege.
```

O papel de Vendas nem se conecta ao banco da auditoria, e o mesmo vale para o papel de cada perfil. As ferramentas usam esses papéis, então nenhuma delas chega à auditoria (RF-32).

O papel `auditoria`, com que o servidor MCP grava, só insere. A senha é o valor de `SENHA_DO_PAPEL_AUDITORIA`:

```
docker compose exec postgres psql -h 127.0.0.1 -U auditoria -d auditoria
```

Dentro do `psql`:

| Comando | Resultado esperado |
| --- | --- |
| `select count(*) from auditoria.chamada;` | `ERROR: permission denied for table chamada` |
| `update auditoria.chamada set resultado = 'permitida';` | `ERROR: permission denied for table chamada` |
| `delete from auditoria.chamada;` | `ERROR: permission denied for table chamada` |

Nem um erro no servidor MCP apaga ou expõe o registro.

## 8. Devolver o limite alto e a suíte

A suíte faz centenas de chamadas com o mesmo usuário e precisa do servidor MCP com o limite alto. Depois da demonstração, na raiz do projeto:

```
LIMITE_DE_CHAMADAS_POR_USUARIO=100000 docker compose up -d --wait mcp
```

No PowerShell, defina a variável antes: `$env:LIMITE_DE_CHAMADAS_POR_USUARIO = "100000"; docker compose up -d --wait mcp` (e `Remove-Item Env:LIMITE_DE_CHAMADAS_POR_USUARIO` ao terminar). Com o limite padrão, a suíte para logo no começo e avisa. Então, dentro de `backend/`, `uv run pytest`, como na seção Testes do README. O limite de verdade é testado com o servidor criado dentro do processo, com um limite baixo e um relógio falso.

Os testes novos da entrega 4b:

| Arquivo | Testes | O que verifica |
| --- | --- | --- |
| `test_auditoria_das_chamadas.py` | 1 | A chamada permitida ao serviço `mcp` do compose já está na auditoria quando a resposta chega |
| `test_desfechos_na_auditoria.py` | 17 | O servidor criado no processo, gravando na auditoria do ambiente: outro perfil e nome inexistente como `negada`, com o nome pedido; parâmetro inválido como chegou; consulta que falhou e erro interno como `falha`; argumentos e nome grandes cortados; listar e o 401 sem linha; sem auditoria, a chamada recusada com serviço indisponível |
| `test_limite_de_frequencia.py` | 8 | Com limite baixo e relógio falso: a chamada além do limite barrada e registrada como `limitada`; outro usuário do mesmo perfil não afetado; negadas e com parâmetro inválido contam; barradas e listar não contam; a volta quando a janela passa; o padrão de 30 por 60 s e as variáveis de ambiente |
| `test_protecao_da_auditoria.py` | 8 | O papel `auditoria` insere e não lê, não altera nem apaga; a recarga preserva uma linha gravada antes dela e só reaplica a senha; o papel de cada perfil não se conecta ao banco da auditoria |

Os testes da matriz da 4a (`test_ferramentas_de_vendas.py`) passaram a conferir, depois de cada chamada, a linha da auditoria: usuário, perfil, ferramenta, parâmetros e resultado.

Requisitos cobertos:

| Requisito | Onde |
| --- | --- |
| RF-30 Toda chamada registrada com usuário, perfil, ferramenta, parâmetros, resultado e horário | `test_auditoria_das_chamadas.py`, `test_ferramentas_de_vendas.py`; passo 3 |
| RF-31 Chamada negada registrada | `test_desfechos_na_auditoria.py`, `test_ferramentas_de_vendas.py`; passo 4 |
| RF-32 Nenhuma ferramenta lê a auditoria | `test_protecao_da_auditoria.py`; passo 7 |
| RS-11 Limite de chamadas por usuário | `test_limite_de_frequencia.py`; passo 5 |
| CA-07 Chamadas permitidas e negadas na auditoria | `test_ferramentas_de_vendas.py`, `test_desfechos_na_auditoria.py`; passos 3 a 6 |

## Encerrar

```
docker compose down -v
```
