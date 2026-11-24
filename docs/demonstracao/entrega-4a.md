# Roteiro de demonstração: entrega 4a, servidor MCP de Vendas

Este roteiro mostra a entrega 4a no MCP Inspector: o servidor MCP de Vendas, as cinco ferramentas que só o perfil Vendas lista e chama, a lista vazia dos outros perfis, a recusa do token emitido para outra aplicação e a recusa de um parâmetro fora do previsto. Cada passo traz o comando e o resultado esperado com a configuração padrão (semente 20261130, data de referência 30/11/2026). Os comandos rodam na raiz do projeto, salvo quando o passo indica `backend/`. Onde o PowerShell e o bash diferem, o passo mostra os dois.

Pré-requisitos: Docker com Docker Compose, [uv](https://docs.astral.sh/uv/), Node.js na versão que o MCP Inspector 2.16 exige (`^22.23.4`, `^24.22.1` ou `>=26.12.1`) e um navegador. O roteiro fixa o Inspector em `@modelcontextprotocol/inspector@2.16.0`, a versão em que ele foi conferido.

**O que foi conferido e como.** Os resultados esperados abaixo foram observados no ambiente local em 24/11/2026, com o Inspector 2.16.0, no modo de linha de comando (`--cli`) e na interface do navegador: o login pela interface, a lista das cinco ferramentas para `ana.vendas`, as chamadas com os números do passo 4, a lista vazia de `diego.diretoria` e a recusa do token de outra aplicação (passo 6).

## 1. Preparar a configuração e subir

```
cp backend/.env.example backend/.env
docker compose down -v
docker compose up -d --build --wait
```

O `backend/.env` ganhou uma variável nesta entrega: `ENDERECO_PUBLICO_DO_MCP=http://localhost:8001`, o endereço que o servidor MCP anuncia nos metadados de recurso protegido. Quem já tem um `.env` de antes precisa acrescentá-la; sem ela o serviço `mcp` não sobe. Ela precisa ser o endereço que o cliente digita (`localhost`, a porta de `MCP_PORT`).

O compose sobe o Postgres, roda a carga, sobe o Keycloak, a API, o **servidor MCP** (serviço `mcp`, em `http://127.0.0.1:8001/mcp`) e o frontend, e termina com os contêineres `Healthy` e a carga `Exited`. O servidor MCP só fica saudável depois da carga e do Keycloak.

## 2. A descoberta OAuth, pelo terminal

No PowerShell, use `curl.exe` no lugar de `curl`.

```
curl -i -X POST http://localhost:8001/mcp
```

```
HTTP/1.1 401 Unauthorized
www-authenticate: Bearer resource_metadata="http://localhost:8001/.well-known/oauth-protected-resource/mcp"
```

Sem token não há resposta do protocolo: só o 401, que aponta onde estão os metadados de recurso protegido (RFC 9728).

```
curl http://localhost:8001/.well-known/oauth-protected-resource/mcp
```

```
{"resource":"http://localhost:8001/mcp","authorization_servers":["http://localhost:8080/realms/pulso"],"scopes_supported":["openid"],"bearer_methods_supported":["header"]}
```

Os metadados dizem ao cliente do protocolo MCP que o servidor de autorização é o realm `pulso` do Keycloak. É por aqui que o Inspector descobre onde fazer login.

## 3. Abrir o Inspector e entrar como Vendas

1. Numa janela do terminal (qualquer pasta):

   ```
   npx @modelcontextprotocol/inspector@2.16.0
   ```

   O Inspector abre no navegador, com um token de sessão do próprio Inspector na URL (`?MCP_PROXY_AUTH_TOKEN=...`; o link também aparece no terminal).
2. **Troque `127.0.0.1` por `localhost` na barra de endereço do navegador**, mantendo o resto da URL, e aperte Enter. O Inspector costuma abrir em `http://127.0.0.1:6274` e monta o retorno do login a partir do endereço da página; o realm só aceita `http://localhost:6274/oauth/callback`, e com `127.0.0.1` o Keycloak mostra "Parâmetro inválido: redirect_uri".
3. **Saia de qualquer sessão do pulso no navegador** antes de conectar: abra `http://localhost:8080/realms/pulso/protocol/openid-connect/logout` e confirme, ou use uma janela anônima. Se o navegador já estiver logado na aplicação, o Keycloak reaproveita essa sessão, não mostra a tela de login, e o Inspector entra com o usuário dela (por exemplo, `diego.diretoria`, com a lista vazia).
4. **Add Server** → **Add manually**:
   - **Transport**: **Streamable HTTP**;
   - **URL**: `http://localhost:8001/mcp` (exatamente essa: o `resource` dos metadados precisa casar com ela);
   - em **OAuth Settings**, **Client ID** `pulso-inspector`, sem **Client Secret**, e confira que o **Redirect URI** mostrado (não editável) é `http://localhost:6274/oauth/callback`.

   **Import from client config** não serve aqui: ele só importa configurações de Claude Code, Cline, Cursor e VS Code, sem campo para colar um JSON.
5. **Connect**. Esperado: o Inspector recebe o 401, lê os metadados do passo 2 e os do realm e leva à **tela de login do pulso** (o tema do realm, a mesma da aplicação).
6. Entre como `ana.vendas` (senha em `SENHA_DO_USUARIO_VENDAS`). Esperado: o navegador volta ao Inspector, conectado.
7. Em **Tools**, **List Tools**. Esperado: as cinco de Vendas, nesta ordem: `vendas_indicadores`, `vendas_evolucao`, `vendas_situacao_das_entregas`, `vendas_pedidos_recentes` e `vendas_atrasos`, cada uma com título, descrição e o campo `periodo` (enumeração `30d`, `90d`, `12m`, `24m`, padrão `12m`); `vendas_atrasos` também com `agrupamento` (`rota` ou `lojista`, obrigatório).
8. Clique em cada ferramenta, preencha os campos e **Run Tool**. Os resultados são os da tabela do passo 4.

## 4. As ferramentas como Vendas

As chamadas abaixo usam o modo de linha de comando do Inspector com o token colado, para que cada resultado esperado possa ser conferido no terminal. Pela interface, depois do passo 3, os resultados são os mesmos.

Dentro de `backend/`, emita o token de `ana.vendas` pelo cliente do Inspector. O comando percorre o mesmo login da tela (código com PKCE) e imprime só o token, que vale 5 minutos:

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

Liste as ferramentas (a linha é a mesma nos dois terminais):

```
npx @modelcontextprotocol/inspector@2.16.0 --cli http://localhost:8001/mcp --transport http --stored-auth-only --header "Authorization: Bearer $TOKEN" --method tools/list
```

Resultado esperado: um JSON com `"tools"` e as cinco ferramentas do passo 3, cada uma com `inputSchema` de `"additionalProperties": false` e `annotations` `readOnlyHint: true`. O `--stored-auth-only` impede o Inspector de abrir um login quando o token é recusado (passo 6).

Para chamar uma ferramenta, troque o final da linha por `--method tools/call --tool-name <ferramenta>` e acrescente `--tool-arg <parâmetro>=<valor>` quando quiser. Cada resposta traz o resultado em `structuredContent` (e o mesmo JSON como texto em `content`), com `"isError": false`:

| Chamada | Resultado esperado |
| --- | --- |
| `--tool-name vendas_indicadores` | `periodo` de `2025-12-01` a `2026-11-30`; `pedidos_realizados` 16795 (anterior 13204); `receita` 17082039.33 (anterior 13543930.03); `taxa_de_atraso` 0.0903 com `atrasos` 1411 (anterior 0.1021); `taxa_de_aprovacao` 0.9595 (anterior 0.9599). Os mesmos números do painel da entrega 3. |
| `--tool-name vendas_evolucao --tool-arg periodo=90d` | `periodo` de `2026-09-02` a `2026-11-30`; `agrupamento` `semana`, 14 pontos, do `2026-08-31` (211 pedidos, parcial) ao `2026-11-30` (83 pedidos, parcial). |
| `--tool-name vendas_situacao_das_entregas` | Em trânsito 436, Prazo vencido 57, Entregue no prazo 14211, Entregue com atraso 1411. |
| `--tool-name vendas_pedidos_recentes --tool-arg periodo=30d` | `periodo` de `2026-11-01` a `2026-11-30` e 20 pedidos, do 29999 ao 29980, com número, momento da compra, cidade, UF, lojista, rota, valor, pagamento e entrega; nenhum identificador nem dado pessoal de cliente. |
| `--tool-name vendas_atrasos --tool-arg agrupamento=rota` | Ver abaixo. |
| `--tool-name vendas_atrasos --tool-arg agrupamento=lojista` | Ver abaixo. |

**Onde o atraso se concentra** (a pergunta sugerida de Vendas, "O que está causando os atrasos?"). As duas chamadas de `vendas_atrasos` trazem o mesmo total do período de 12 meses: 15.622 pedidos entregues, 1.411 atrasos, taxa de atraso de 9,0%. Pedidos com prazo vencido e em trânsito não entram. Cada grupo traz `entregues`, `atrasos`, `taxa_de_atraso` e `participacao` (a fração dos atrasos do período), ordenados pelo número de atrasos; vêm só os 10 primeiros, com `lista_cortada: true` e o número total de grupos com atraso.

Por rota (`grupos_com_atraso` 255):

| Rota | Entregues | Atrasos | Taxa de atraso | Participação |
| --- | --- | --- | --- | --- |
| SP → SP | 2270 | 121 | 5,3% | 8,6% |
| SP → RJ | 935 | 61 | 6,5% | 4,3% |
| PE → SP | 266 | 51 | 19,2% | 3,6% |
| SP → MG | 634 | 40 | 6,3% | 2,8% |
| SP → RS | 283 | 38 | 13,4% | 2,7% |
| SP → CE | 203 | 32 | 15,8% | 2,3% |
| SP → PE | 196 | 30 | 15,3% | 2,1% |
| SP → AM | 131 | 29 | 22,1% | 2,1% |
| SP → PA | 142 | 27 | 19,0% | 1,9% |
| SP → BA | 273 | 25 | 9,2% | 1,8% |

Por rota o atraso se espalha: a rota com mais atrasos, SP → SP, tem só 8,6% deles, e com taxa abaixo da média; as rotas para o Norte e o Nordeste têm taxas de 15% a 22%, mas pouco volume.

Por lojista (`grupos_com_atraso` 167):

| Lojista | Entregues | Atrasos | Taxa de atraso | Participação |
| --- | --- | --- | --- | --- |
| Vasconcelos | 1758 | 323 | 18,4% | 22,9% |
| Siqueira | 545 | 164 | 30,1% | 11,6% |
| Casa Grande da Cunha Ltda. | 297 | 86 | 29,0% | 6,1% |
| Câmara Cirino S.A. | 278 | 65 | 23,4% | 4,6% |
| Pinto Pires Ltda. | 164 | 48 | 29,3% | 3,4% |
| Fogaça | 125 | 43 | 34,4% | 3,0% |
| Cirino S.A. | 209 | 35 | 16,7% | 2,5% |
| Andrade - ME | 159 | 31 | 19,5% | 2,2% |
| Abreu e Filhos | 146 | 30 | 20,5% | 2,1% |
| Mendonça Araújo S.A. | 116 | 29 | 25,0% | 2,1% |

Por lojista o atraso se concentra: dois lojistas, Vasconcelos e Siqueira, somam 34,5% dos atrasos do período, com taxas de 18% e 30% contra 9% da média. É a resposta que o agente da entrega 5a vai dar à pergunta sugerida.

## 5. Outro perfil: a lista vazia

Emita o token de `bruno.produtos` como no passo 4 (`... token_de_demonstracao bruno.produtos pulso-inspector`) e liste de novo:

```
npx @modelcontextprotocol/inspector@2.16.0 --cli http://localhost:8001/mcp --transport http --stored-auth-only --header "Authorization: Bearer $TOKEN" --method tools/list
```

```
{
  "tools": []
}
```

Com `carla.comercial` e `diego.diretoria`, o mesmo: ainda não há ferramentas desses perfis (RF-21).

Pela interface: em **Server Settings**, **Clear OAuth state and disconnect**; encerre a sessão do provedor (abra `http://localhost:8080/realms/pulso/protocol/openid-connect/logout` e confirme, ou use uma janela anônima); conecte de novo e entre como `bruno.produtos`. Esperado: **Tools** → **List Tools** vazio. Sem encerrar a sessão do provedor, o Inspector volta conectado como o usuário anterior, sem tela de login.

**A chamada direta pelo nome.** O Inspector só chama o que a lista mostrou: no modo de linha de comando, `--tool-name vendas_indicadores` com o token de Bruno termina com `Tool 'vendas_indicadores' not found on server.`, uma conferência feita pelo próprio Inspector, sem chamar o servidor. Para mostrar o que o servidor responde (RF-22), mande a chamada crua, com o token de Bruno ainda em `$TOKEN`.

bash:

```
curl -s -X POST http://localhost:8001/mcp -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vendas_indicadores","arguments":{}}}'
```

PowerShell:

```
$corpo = '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vendas_indicadores","arguments":{}}}'
Invoke-RestMethod -Method Post http://localhost:8001/mcp -Headers @{Authorization="Bearer $TOKEN"; Accept="application/json, text/event-stream"} -ContentType "application/json" -Body $corpo | ConvertTo-Json -Depth 5
```

```
{"jsonrpc":"2.0","id":1,"result":{"content":[{"text":"Ferramenta desconhecida.","type":"text"}],"isError":true}}
```

No PowerShell, o mesmo conteúdo sai formatado em várias linhas.

Troque `vendas_indicadores` por `nao_existe`: a resposta é a mesma, byte a byte. Quem não tem acesso não descobre que a ferramenta existe (RS-08), e a mensagem não repete o nome pedido. Com `vendas_atrasos` e `"arguments":{"agrupamento":"uf"}`, também a mesma: o perfil é negado antes de qualquer validação de parâmetro.

## 6. O token de outra aplicação (CA-03)

O comando de token emite, para o mesmo usuário e pelo mesmo provedor, um token do cliente `pulso-outra-aplicacao`: real, válido, com perfil `vendas`, mas com destinatário só `pulso-outra-aplicacao`, sem `pulso-mcp`. Dentro de `backend/`, emita-o como no passo 4, com `... token_de_demonstracao ana.vendas pulso-outra-aplicacao`, e liste:

```
npx @modelcontextprotocol/inspector@2.16.0 --cli http://localhost:8001/mcp --transport http --stored-auth-only --header "Authorization: Bearer $TOKEN" --method tools/list
```

```
{"error":{"code":"auth_required","message":"Error POSTing to endpoint: {\"error\": \"invalid_token\", \"error_description\": \"Authentication failed. The provided bearer token is invalid, expired, or no longer recognized by the server. ...\"}"}}
```

O servidor responde 401 com `WWW-Authenticate: Bearer error="invalid_token", ..., resource_metadata="http://localhost:8001/.well-known/oauth-protected-resource/mcp"`, a mesma recusa de qualquer token inválido: não diz qual verificação falhou. O motivo fica no log do servidor (`docker compose logs mcp`), como `token recusado: Audience doesn't match`. O mesmo token também é recusado pela API.

Pela interface, **encerre antes a sessão do provedor** (logout ou janela anônima, como no passo 3). Em **Server Settings**, **Clear OAuth state and disconnect**; em **Custom Headers**, **+ Add Header** com o nome `Authorization` e o valor `Bearer ` seguido do token; **Connect**. Esperado: o servidor recusa o token (`token recusado: Audience doesn't match` no `docker compose logs mcp`) e o Inspector, por causa do 401, leva à tela de login do pulso em vez de conectar; não entre nela neste passo. Se a sessão do provedor ainda estiver aberta, o Inspector faz esse login sozinho, sem mostrar a tela, recebe um token novo do `pulso-inspector` e **conecta**: o log mostra a recusa seguida de requisições aceitas. A recusa aconteceu, mas a tela não a mostra; por isso, na apresentação, prefira a linha de comando acima, com o log ao lado.

## 7. Parâmetro fora do previsto

Com o token de `ana.vendas` do passo 4 (emita outro se passaram 5 minutos):

```
npx @modelcontextprotocol/inspector@2.16.0 --cli http://localhost:8001/mcp --transport http --stored-auth-only --header "Authorization: Bearer $TOKEN" --method tools/call --tool-name vendas_atrasos --tool-arg agrupamento=uf
```

```
{
  "content": [
    {
      "type": "text",
      "text": "Parâmetro inválido."
    }
  ],
  "isError": true
}
```

Depois do resultado, o Inspector acrescenta `{"error":{"code":"tool_is_error",...}}` e termina com código 5: é o jeito dele de dizer que a ferramenta devolveu erro. O mesmo `Parâmetro inválido.`, sem eco do valor nem descrição do esquema (RF-23, RS-08), vem para:

- `--tool-name vendas_indicadores --tool-arg periodo=7d` (fora da enumeração);
- `--tool-name vendas_atrasos` sem `agrupamento` (obrigatório);
- `--tool-name vendas_indicadores --tool-arg periodo=12m --tool-arg filtro=x` (parâmetro a mais).

Pela interface, o campo `agrupamento` é uma lista fechada; para mandar um valor fora dela, use a linha de comando.

## 8. Caminho alternativo: o token colado

Se o login pelo Inspector falhar no dia, os passos 4 a 7 já usam o token colado e não dependem dele. Na interface:

1. Dentro de `backend/`, emita o token como no passo 4 e copie-o (`ana.vendas` com `pulso-inspector`; com `pulso-web` também funciona, porque o token da aplicação tem os dois destinatários, ADR 0006).
2. No Inspector, em **Server Settings** do servidor `http://localhost:8001/mcp`, **Clear OAuth state and disconnect**; em **Custom Headers**, **+ Add Header**: nome `Authorization`, valor `Bearer ` seguido do token.
3. Conecte. Esperado: as cinco ferramentas, sem passar pela tela de login.

O token vale 5 minutos e deixa de valer se o Keycloak for reiniciado; emita outro e troque o valor do cabeçalho. Pela linha de comando, o caminho foi conferido nos passos 4 a 7.

## 9. A suíte

Com o ambiente no ar, dentro de `backend/`:

```
uv run pytest
```

Resultado esperado: `601 passed`, em cerca de 11 minutos e meio (`601 passed in 691.35s` em 24/11/2026). A suíte recarrega o banco e reinicia o Keycloak, então ela vem depois da demonstração.

Uma execução anterior falhou uma vez em `test_o_provedor_libera_ao_navegador_so_a_origem_do_inspector`, com `Refresh token issued before the user session started` na renovação. A causa é o relógio da máquina virtual do Docker Desktop, onde o Keycloak roda: ele fica uns 12 s atrás do relógio do Windows e, a cada 15 a 20 s, salta para a hora certa por um instante e volta. A sessão aberta durante o salto começa depois do `iat` do token emitido logo em seguida, e o Keycloak recusa renovar um token emitido antes do início da sessão. Não tem relação com o reinício do provedor nem com a ordem dos testes: aconteceu também fora da suíte, em 4 de 60 logins seguidos de renovação. O teste passou a usar a troca do código, o mesmo endpoint de token, que não faz essa comparação.

Os testes novos da entrega 4a:

| Arquivo | Testes | O que verifica |
| --- | --- | --- |
| `test_ferramentas_de_vendas.py` | 99 | Protocolo MCP contra o serviço `mcp` do compose, com tokens reais: os quatro usuários contra as cinco ferramentas (lista e chamada só para Vendas, lista vazia para os outros); a chamada direta de outro perfil com o mesmo erro de uma ferramenta inexistente; as quatro ferramentas do painel com o mesmo conteúdo das rotas da API; toda resposta com as datas do período; nenhuma resposta com identificador de cliente ou nome interno do banco; sem estado entre requisições |
| `test_atrasos_de_vendas.py` | 57 | `vendas_atrasos` nos dois agrupamentos e nos quatro períodos, contra consultas independentes com o papel dono: totais, ordenação, limite de 10, participação e exclusão do prazo vencido; nomes de lojista únicos na carga padrão |
| `test_tokens_forjados_no_mcp.py` | 92 | O servidor criado no processo, com tokens forjados: outro emissor, outra chave, sem assinatura, assinatura simétrica, outro destinatário (inclusive só `pulso-api`), vencido, ainda não válido, sem perfil conhecido; a ordem token, perfil, parâmetros; parâmetro a mais ou fora da enumeração sem eco; um `perfil` enviado por quem chama não muda o do token; banco e provedor fora do ar como indisponibilidade |
| `test_registro_de_ferramentas.py` | 13 | Toda ferramenta publicada vem do registro e serve uma consulta com perfil; esquemas só com os parâmetros previstos, enumerações fechadas e sem propriedades adicionais; descrição em toda ferramenta e parâmetro |
| `test_token_de_outra_aplicacao.py` | 10 | O token real de `pulso-outra-aplicacao` recusado pelo MCP do compose e pela API (CA-03) |
| `test_descoberta_oauth.py` | 5 | O 401 aponta os metadados de recurso protegido; os metadados apontam o realm; sem CORS |
| `test_login_pelo_inspector.py` | 14 | O cliente `pulso-inspector` no realm (público, PKCE, retorno do Inspector), o token dele aceito pelo MCP e recusado pela API, os metadados do realm sem `offline_access` e o registro dinâmico de clientes desligado |
| `test_comando_de_token.py` | 11 | O comando de token de demonstração, rodado como o apresentador o roda |

Requisitos cobertos:

| Requisito | Onde |
| --- | --- |
| RF-19 Ferramentas somente leitura, orientadas a perguntas de negócio | Registro (`test_registro_de_ferramentas.py`); passos 3 e 4 |
| RF-20 Cada ferramenta de um único perfil | `test_registro_de_ferramentas.py` |
| RF-21 A lista só com as ferramentas do perfil | `test_ferramentas_de_vendas.py`; passo 5 |
| RF-22 A chamada verifica o perfil de novo | `test_ferramentas_de_vendas.py`, `test_tokens_forjados_no_mcp.py`; passo 5 |
| RF-23 Só parâmetros previstos e validados | `test_tokens_forjados_no_mcp.py`, `test_registro_de_ferramentas.py`; passo 7 |
| RF-24 Descrição clara | `test_registro_de_ferramentas.py`; passo 3 |
| RF-25 Respostas estruturadas e limitadas | `test_atrasos_de_vendas.py`, `test_ferramentas_de_vendas.py`; passo 4 |
| RF-26 Sem estado entre requisições | `test_ferramentas_de_vendas.py` |
| CA-02 (ferramentas) Todos os perfis contra todas as ferramentas | `test_ferramentas_de_vendas.py` |
| CA-03 Token de outra aplicação recusado | `test_token_de_outra_aplicacao.py`; passo 6 |

## 10. A integração contínua roda em um pull request

Todo pull request para `homolog` ou `main` roda os dois checks. O de **Estilo e testes** sobe o ambiente com o serviço `mcp` e roda a suíte inteira, com os testes do servidor MCP.

## Encerrar

```
docker compose down -v
```
