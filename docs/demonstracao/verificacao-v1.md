# Roteiro de verificação V1: Claude e ChatGPT pelo túnel

Este roteiro mostra a verificação V1: o ambiente local publicado por um túnel rápido do `cloudflared`, um assistente externo que se registra sozinho no provedor (registro dinâmico), leva ao login do pulso como `ana.vendas` e chama as ferramentas de Vendas do servidor MCP, e `diego.diretoria` vendo a lista de ferramentas vazia. Cada passo traz o comando e o resultado esperado com a configuração padrão (semente 20261130, data de referência 30/11/2026). Os comandos rodam na raiz do projeto. Onde o PowerShell e o bash diferem, o passo mostra os dois.

Pré-requisitos: Docker com Docker Compose, um navegador, acesso à internet e uma conta em cada assistente: no Claude (claude.ai), uma conta que permita adicionar conector personalizado; no ChatGPT, uma conta com o modo desenvolvedor (plano pago). O túnel não exige conta na Cloudflare.

**O que foi conferido e como.** Em 24/11/2026, com cloudflared 2026.10.7, Keycloak 26.4.2 e nginx 1.30.7, pelo endereço do túnel: os metadados de recurso protegido e os do realm (passo 4), a tela de login com o tema do pulso e, no **Claude**, o conector personalizado completo: registro automático, login de `ana.vendas`, consentimento, conector conectado e chamadas ao servidor MCP respondidas com 200 (passo 5); `diego.diretoria` conectado com a lista de ferramentas vazia (passo 6). Os números da resposta do Claude à pergunta do passo 5 não foram anotados (ver Lacunas). O plano da conta do Claude usada não foi registrado. A aplicação local também foi conferida pelo túnel, sem navegador: o login de `ana.vendas` pelo fluxo de código com o cliente `pulso-web`, contra o emissor do túnel, deu um token que a API aceitou em `GET /eu`, com a resposta `{"nome": "Ana Ribeiro", "perfil": "vendas"}`, e o `/configuracao.json` do frontend apontava o provedor para o túnel. O **ChatGPT não foi verificado**, por decisão do usuário: o passo 7 traz os passos esperados, e a verificação fica para a entrega 11, pelo túnel (ver Lacunas).

## Ambiente da verificação

| Item | Valor |
| --- | --- |
| Data | 24/11/2026 |
| Túnel | `cloudflare/cloudflared:2026.10.7`, túnel rápido (`*.trycloudflare.com`) |
| Provedor de identidade | Keycloak 26.4.2 |
| Proxy reverso | `nginx:1.30.7-alpine` |
| Claude | claude.ai, conector personalizado; plano não registrado |
| ChatGPT | Não verificado |

## 1. Preparar a configuração e subir no modo local

```
cp backend/.env.example backend/.env
docker compose down -v
docker compose up -d --build --wait
```

**Troque as senhas antes de expor o ambiente.** As senhas do `backend/.env.example` (`KC_BOOTSTRAP_ADMIN_PASSWORD` e as quatro `SENHA_DO_USUARIO_*`) são públicas, estão no repositório. Com o túnel ligado, a tela de login do pulso fica na internet: ponha senhas suas no `backend/.env` antes do passo 3.

Além dos serviços da entrega 4a, o compose sobe o **proxy reverso** (serviço `proxy`, em `http://127.0.0.1:8088`, porta configurável por `PROXY_PORT`), que reúne sob um endereço só as rotas do realm `pulso`, os arquivos do tema, o protocolo do servidor MCP e os metadados de recurso protegido. Ele só é publicado na máquina local. O túnel (serviço `tunel`) não sobe: ele fica atrás do perfil `tunel`.

## 2. O proxy, pelo terminal

No PowerShell, use `curl.exe` no lugar de `curl`.

```
curl http://localhost:8088/.well-known/oauth-protected-resource/mcp
```

Esperado: o mesmo JSON que o servidor MCP devolve direto em `http://localhost:8001`, com `"scopes_supported":["openid","pulso-mcp"]`. O escopo `pulso-mcp` é o que o assistente pede para o token valer no servidor MCP (ADR 0007).

```
curl -i http://localhost:8088/admin/
```

Esperado: `HTTP/1.1 404 Not Found`. O console de administração, o realm `master` e qualquer caminho que um assistente não usa não passam pelo proxy, e por isso não passam pelo túnel.

## 3. Ligar o túnel

1. Suba o túnel:

   ```
   docker compose --profile tunel up -d --wait
   ```

2. Leia o endereço do túnel no log.

   PowerShell:

   ```
   docker compose logs tunel | Select-String trycloudflare.com
   ```

   bash:

   ```
   docker compose logs tunel | grep trycloudflare.com
   ```

   Esperado: uma linha com um endereço como `https://exemplo-de-tunel.trycloudflare.com`. O endereço muda a cada execução do túnel.
3. No `backend/.env`, ponha esse endereço base (sem barra no fim e sem `/mcp`) nas duas variáveis:

   ```
   ENDERECO_PUBLICO_DO_PROVEDOR=https://exemplo-de-tunel.trycloudflare.com
   ENDERECO_PUBLICO_DO_MCP=https://exemplo-de-tunel.trycloudflare.com
   ```

   No modo túnel o mesmo endereço é o emissor dos tokens (com o caminho do realm) e o endereço público do servidor MCP.
4. Suba o compose de novo, **sem o perfil**:

   ```
   docker compose up -d --wait
   ```

   Isso recria quem depende dos endereços (provedor, API, servidor MCP, frontend) e deixa o túnel no ar com o mesmo endereço. Com `--profile tunel`, o compose recriaria também o túnel, que ganharia um endereço novo, diferente do que está no `.env`.

A aplicação local continua em `http://localhost:5173`, com o login passando pelo endereço do túnel.

Daqui em diante, guarde o endereço numa variável do terminal.

PowerShell:

```
$TUNEL = "https://exemplo-de-tunel.trycloudflare.com"
```

bash:

```
TUNEL=https://exemplo-de-tunel.trycloudflare.com
```

## 4. A descoberta pelo túnel

```
curl "$TUNEL/.well-known/oauth-protected-resource/mcp"
```

```
{"resource":"https://exemplo-de-tunel.trycloudflare.com/mcp","authorization_servers":["https://exemplo-de-tunel.trycloudflare.com/realms/pulso"],"scopes_supported":["openid","pulso-mcp"],"bearer_methods_supported":["header"]}
```

O `resource` é o endereço do túnel com `/mcp`, a URL que se digita no assistente, e o servidor de autorização é o realm `pulso` no mesmo endereço.

```
curl "$TUNEL/realms/pulso/.well-known/openid-configuration"
```

Esperado: os metadados do realm, com `issuer` igual a `$TUNEL/realms/pulso` e um `registration_endpoint` (`$TUNEL/realms/pulso/clients-registrations/openid-connect`): é por ele que o assistente se registra sozinho (RF-28). Os mesmos metadados respondem em `$TUNEL/.well-known/openid-configuration/realms/pulso` e `$TUNEL/.well-known/oauth-authorization-server/realms/pulso`, os caminhos da raiz que alguns SDKs tentam primeiro.

Pelo túnel, a tela de login aparece com o tema do pulso, a mesma da aplicação (passo 5).

## 5. Claude: conector personalizado, login como Vendas

1. **Saia de qualquer sessão do pulso no navegador** antes de conectar: abra `$TUNEL/realms/pulso/protocol/openid-connect/logout` e confirme, ou use uma janela anônima. Com uma sessão aberta, o provedor não mostra a tela de login e o conector entra com o usuário dela.
2. No claude.ai, **Configurações** → **Conectores** → **Adicionar conector personalizado**:
   - **Nome**: livre (por exemplo, `pulso`);
   - **URL**: `$TUNEL/mcp`, com o endereço do túnel por extenso (exatamente essa: o `resource` dos metadados precisa casar com ela);
   - **Autenticação**: **Entrar agora**;
   - **Cliente OAuth**: **Registrar automaticamente** (registro dinâmico). **Não use "Usar a identidade publicada do Claude"**: ela usa um Client ID Metadata Document, que o Keycloak 26.4 não suporta;
   - **Cabeçalhos**: em branco.
3. Confirme. Esperado: o Claude se registra no provedor e abre a **tela de login do pulso**.
4. Entre como `ana.vendas` (senha em `SENHA_DO_USUARIO_VENDAS`). Esperado: a tela de consentimento do provedor, **"Consultar o pulso. com o seu perfil"**: o registro anônimo exige que o usuário confirme o acesso em nome dele. Aceite.
5. Esperado: o conector aparece conectado no Claude, com as cinco ferramentas de Vendas (`vendas_indicadores`, `vendas_evolucao`, `vendas_situacao_das_entregas`, `vendas_pedidos_recentes` e `vendas_atrasos`). No log do servidor MCP (`docker compose logs mcp`), as chamadas do Claude respondem 200.
6. Numa conversa com o conector ligado, pergunte, por exemplo, "Quais são os indicadores de vendas dos últimos 12 meses?". Esperado: o Claude chama `vendas_indicadores` e responde com os números do painel de Vendas e do passo 4 do roteiro da 4a: 16.795 pedidos realizados (13.204 no período anterior), receita de R$ 17.082.039,33, taxa de atraso de 9,0% (1.411 atrasos) e taxa de aprovação de 95,95%. Para conferir lado a lado, abra o painel em `http://localhost:5173` como `ana.vendas`, no período de 12 meses.

O token que o Claude recebe sai com o destinatário `pulso-mcp`, sem `pulso-api`: ele vale no servidor MCP e é recusado pela API (ADR 0006, ADR 0007).

## 6. Outro perfil: a lista vazia

1. No Claude, remova o conector (ou desconecte-o).
2. Encerre a sessão do pulso no navegador: `$TUNEL/realms/pulso/protocol/openid-connect/logout`, ou janela anônima.
3. Adicione o conector de novo, como no passo 5, e entre como `diego.diretoria`.

Esperado: o conector conecta, mas a lista de ferramentas vem vazia: ainda não há ferramentas da Diretoria, e as de Vendas não aparecem para outro perfil (RF-21).

## 7. ChatGPT: modo desenvolvedor (não verificado)

**Este passo não foi executado na V1.** São os passos esperados, a conferir na entrega 11, pelo túnel. O endereço de retorno do ChatGPT, `https://chatgpt.com/connector_platform_oauth_redirect`, já está nos hosts confiáveis do registro anônimo, e o registro com ele é coberto por teste automático (`test_registro_dinamico.py`), sem o ChatGPT.

1. Saia da sessão do pulso no navegador, como no passo 5.
2. No ChatGPT, **Settings** → **Apps & Connectors** → **Advanced** → ligue o **Developer mode**.
3. Em **Apps & Connectors**, **Create**:
   - **Name**: livre;
   - **MCP Server URL**: `$TUNEL/mcp`, com o endereço por extenso;
   - **Authentication**: **OAuth**, com registro dinâmico de cliente (sem Client ID fixo).
4. Confirme. Esperado: o ChatGPT se registra, leva à tela de login do pulso; entre como `ana.vendas` e aceite o consentimento.
5. Numa conversa com o conector ligado (no modo desenvolvedor), faça a mesma pergunta do passo 5. Esperado: os mesmos números do painel, pelo mesmo servidor, sem versão separada para o ChatGPT (RF-27).

Se o ChatGPT recusar algum passo, anote a mensagem que ele mostra e o que aparece em `docker compose logs keycloak` e `docker compose logs mcp`, como foi feito com o Claude na seção de ajustes.

## 8. Voltar ao modo local

1. No `backend/.env`, ponha os valores locais de volta:

   ```
   ENDERECO_PUBLICO_DO_PROVEDOR=http://localhost:8080
   ENDERECO_PUBLICO_DO_MCP=http://localhost:8001
   ```

2. Desligue o túnel e suba o compose de novo:

   ```
   docker compose stop tunel
   docker compose up -d --wait
   ```

**Não deixe o túnel ligado.** Enquanto ele está no ar, o registro de clientes e o servidor MCP ficam na internet, sem limite de frequência (que chega na entrega 4b).

**Reiniciar o provedor ou trocar o endereço do túnel apaga os clientes registrados.** O realm é reimportado a cada subida (ADR 0004), e o endereço do túnel muda a cada execução dele. Nos dois casos o conector do assistente deixa de funcionar: remova-o e adicione-o de novo.

## Ajustes por assistente

### Claude

O Claude exigiu dois ajustes no realm (`keycloak/realm/pulso.json`, commit `680822b`), sem mudança no proxy nem no servidor MCP. Os testes de registro dinâmico passaram a registrar o cliente como o Claude registra.

| O que aconteceu | Mensagem no Claude | Causa | Ajuste |
| --- | --- | --- | --- |
| O registro do cliente era recusado | "Não foi possível fazer o registro no serviço de login..." | O Claude manda no registro os escopos dos metadados, `scope: "openid pulso-mcp"`. A política "Allowed Client Scopes" do registro anônimo recusava `openid` (403, "Not permitted to use specified clientScope"): no Keycloak, `openid` não é um escopo de cliente. | A política passou a aceitar `openid`. |
| O login terminava, mas a conexão falhava | "O Claude não conseguiu concluir a conexão com ... Tente novamente." | Um cliente registrado com escopos fica só com `basic` como escopo padrão, sem `profile`, e o token chegava sem a claim `name`. O servidor MCP o recusava com 401 ("Token is missing the \"name\" claim"). | O escopo `pulso-mcp` passou a trazer o nome do usuário (ADR 0007). |

Também é preciso escolher **Registrar automaticamente** no campo de cliente OAuth: a opção "Usar a identidade publicada do Claude" usa um Client ID Metadata Document, que o Keycloak 26.4 não suporta.

### ChatGPT

Nenhum ajuste registrado: o ChatGPT não foi verificado (ver Lacunas). O endereço de retorno dele já estava previsto nos hosts confiáveis desde o início da V1.

## Lacunas

- **ChatGPT não verificado.** Por decisão do usuário, a V1 fecha só com o Claude. Os passos esperados estão no passo 7; a verificação com o ChatGPT fica para a entrega 11, pelo túnel, junto com os ajustes que ele exigir. O que já se sabe: o retorno `https://chatgpt.com/connector_platform_oauth_redirect` é aceito pelo registro anônimo (teste automático).
- **Plano da conta do Claude não registrado.** Anote-o na próxima verificação.
- **Números da resposta do Claude.** A verificação registrou as chamadas ao servidor MCP com 200, mas não anotou os números da resposta. Na próxima execução, confira-os com o painel, como no passo 5.
- **Client ID Metadata Document.** O Keycloak 26.4 não o suporta. Hoje o Claude oferece o registro dinâmico como alternativa; se um assistente passar a exigir só o CIMD, será preciso outro servidor de autorização (fora do escopo da V1).
- **Clientes registrados não persistem.** Um reinício do provedor ou um túnel novo exige refazer o conector (ADR 0004, ADR 0007).
- **Exposição sem limite de frequência.** Com o túnel ligado, o registro anônimo e o servidor MCP ficam abertos na internet, sem limite até a entrega 4b. Desligue o túnel ao terminar.

## Encerrar

Volte ao modo local (passo 8) e, se quiser apagar tudo:

```
docker compose --profile tunel down -v
```
