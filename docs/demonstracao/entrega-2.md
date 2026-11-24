# Roteiro de demonstração: entrega 2, login e perfil

Este roteiro mostra a entrega 2 inteira, na ordem do roadmap: o provedor de identidade subindo já configurado, a entrada com os quatro usuários de demonstração e a API recusando quem não deve entrar. Cada passo traz o comando e o resultado esperado com a configuração padrão. Os comandos são os mesmos no PowerShell e no bash e rodam na raiz do projeto, salvo quando o passo indica `backend/`.

Pré-requisitos: Docker com Docker Compose, [uv](https://docs.astral.sh/uv/) e um navegador.

## 1. Preparar a configuração

```
cp backend/.env.example backend/.env
```

O `backend/.env` guarda as senhas e não é versionado. Para a demonstração, os valores de exemplo bastam. Quem já tinha um `backend/.env` da entrega 1 precisa copiar de novo, ou acrescentar as variáveis novas do exemplo: o endereço do provedor, o do frontend, o administrador do Keycloak e as senhas dos quatro usuários de demonstração.

## 2. Subir do zero com um comando

Derrube o que estiver no ar, inclusive os volumes, e suba tudo:

```
docker compose down -v
docker compose up -d --build --wait
```

O comando sobe o Postgres, roda a carga, sobe o Keycloak, a API e, por último, o frontend. Ele só termina quando tudo está pronto. Resultado esperado, com código de saída 0, terminando com:

```
 Container workshop-mcp-postgres-1  Healthy
 Container workshop-mcp-keycloak-1  Healthy
 Container workshop-mcp-api-1  Healthy
 Container workshop-mcp-carga-1  Exited
 Container workshop-mcp-frontend-1  Healthy
```

A ordem das linhas pode variar. O Keycloak não guarda estado: ele importou o realm do arquivo versionado `keycloak/realm/pulso.json` ao subir, sem nenhum passo no console de administração. Para ver:

```
docker compose logs keycloak
```

Entre as linhas do log:

```
... Full importing from file /opt/keycloak/bin/../data/import/pulso.json
... Realm 'pulso' imported
... KC-SERVICES0032: Import finished successfully
```

## 3. Guardar um token que vai vencer

O token de acesso vale 5 minutos. Para mostrar a recusa de um token vencido no passo 5, obtenha um agora, antes da parte no navegador, que leva mais que isso. Dentro de `backend/`:

```
uv sync --locked
uv run python tests/demonstracao.py entrar ana.vendas
```

O comando faz o login da Ana pelo mesmo fluxo do navegador (código com PKCE), guarda o token em `backend/.token-da-demonstracao` (não versionado) e pede `GET /eu` à API do ambiente. Resultado esperado, com a hora de agora mais 5 minutos no lugar de `20:22:31`:

```
token de ana.vendas: aud=pulso-api vence às 20:22:31
GET /eu -> 200 {"nome": "Ana Ribeiro", "perfil": "vendas"}
```

O `aud=pulso-api` diz que o token foi emitido para a API. A API aceita o token e devolve o nome e o perfil de quem entrou.

## 4. Os quatro usuários de demonstração entram com o perfil certo

Abra `http://localhost:5173` no navegador. A aplicação leva à tela de login do Keycloak, com o tema do `pulso.`: painel verde-escuro à esquerda, formulário **Entrar** à direita.

Primeiro, uma senha errada: usuário `ana.vendas`, senha qualquer. Resultado esperado: a tela de login de novo, com a mensagem `Usuário ou senha inválidos.`, a mesma para um usuário que não existe e para uma conta bloqueada por excesso de tentativas.

Depois, entre com cada usuário de demonstração. As senhas são os valores das variáveis em `backend/.env`:

| Usuário | Senha | Nome | Perfil |
| --- | --- | --- | --- |
| `ana.vendas` | `SENHA_DO_USUARIO_VENDAS` | Ana Ribeiro | Vendas |
| `bruno.produtos` | `SENHA_DO_USUARIO_PRODUTOS` | Bruno Costa | Produtos |
| `carla.comercial` | `SENHA_DO_USUARIO_COMERCIAL` | Carla Mendes | Comercial |
| `diego.diretoria` | `SENHA_DO_USUARIO_DIRETORIA` | Diego Almeida | Diretoria |

Para cada um, a aplicação volta direto para `http://localhost:5173` e mostra, com o perfil da linha:

- na sidebar, um único item, **Painel de Vendas** (ou de Produtos, Comercial, da Diretoria), e no rodapé o nome e o perfil, por exemplo **Ana Ribeiro** e **Vendas**;
- na topbar, o indicador do perfil, com a cor do perfil, e o botão **Sair**;
- no cabeçalho, **Painel de Vendas** e `Olá, Ana. Aqui você acompanha os dados do seu perfil.`;
- na área de conteúdo, o aviso **O painel chega em breve**.

O nome e o perfil vêm da resposta de `GET /eu`, não do token lido no navegador.

Com o último usuário, recarregue a página (F5): a aplicação volta sem pedir senha, porque a sessão no provedor continua ativa.

Entre um usuário e outro, clique em **Sair**. A sessão termina também no Keycloak e o navegador volta à tela de login, vazia. Depois de sair com o último usuário, abra `http://localhost:5173` de novo: a tela de login aparece, sem entrar em silêncio com o usuário anterior.

## 5. A API recusa quem chega sem token, com token de outro serviço ou com token vencido

Os três pedidos vão à API do ambiente, em `http://127.0.0.1:8000`, a mesma que o navegador usou no passo 4. Toda recusa tem a mesma resposta, que não diz qual verificação falhou. O motivo fica só no log da API, e o comando o mostra na última linha, lido de `docker compose logs api`. Dentro de `backend/`.

**Sem token:**

```
uv run python tests/demonstracao.py sem-token
```

```
GET /eu -> 401 {"erro": "Não autenticado."}
WWW-Authenticate: Bearer
log da API: token recusado: cabeçalho Authorization ausente ou sem Bearer
```

**Token emitido para outro serviço.** O token é verdadeiro: do mesmo provedor e da mesma usuária, com a senha certa. Mas foi emitido para o `admin-cli`, um cliente que existe em todo realm, e não traz a API entre os destinatários:

```
uv run python tests/demonstracao.py outro-servico ana.vendas
```

```
token de ana.vendas para admin-cli: aud=(nenhum)
GET /eu -> 401 {"erro": "Não autenticado."}
WWW-Authenticate: Bearer
log da API: token recusado: Token is missing the "aud" claim
```

**Token vencido.** É o token guardado no passo 3, que a API aceitou com `200`. Passados os 5 minutos:

```
uv run python tests/demonstracao.py vencido
```

```
token de ana.vendas: venceu às 20:22:31
GET /eu -> 401 {"erro": "Não autenticado."}
WWW-Authenticate: Bearer
log da API: token recusado: token vencido
```

Se o token ainda valer, o comando não faz o pedido e diz quanto falta, por exemplo `O token ainda vale: vence às 20:22:31. Espere mais 247 segundos.` A conta usa o relógio do contêiner da API, que pode andar alguns segundos atrás do da máquina, e os 5 segundos de folga de relógio que a API aceita depois do vencimento.

A suíte do passo 6 também mostra a recusa de um token real vencido, sem esperar: `test_eu.py` cria a API com o relógio adiantado além do vencimento de um token recém-emitido.

## 6. A suíte verifica a API contra o Keycloak real

Com o ambiente no ar, dentro de `backend/`:

```
uv run pytest
```

Resultado esperado: `138 passed`, em cerca de três minutos e meio. A suíte recarrega o banco algumas vezes e reinicia o Keycloak, o que encerra as sessões abertas e troca as chaves de assinatura: por isso ela vem depois do passo 5. Os testes da entrega 2 obtêm tokens do Keycloak do compose pelo mesmo fluxo do navegador, sem mocks:

| Arquivo | O que verifica |
| --- | --- |
| `test_eu.py` | Os quatro usuários de demonstração em `GET /eu`; recusa sem token, com cabeçalho mal formado, com token de outro serviço e com token real vencido (relógio adiantado); a API não publica `/docs` nem `/openapi.json` |
| `test_tokens_forjados.py` | Assinatura de outra chave, algoritmo `none` ou HMAC, outro emissor, perfil ausente, duplicado ou desconhecido; todas as recusas idênticas |
| `test_provedor_sem_estado.py` | O Keycloak parte do realm versionado a cada subida |
| `test_tela_de_login.py` | A tela de login com a cara do `pulso.` e a mesma mensagem para usuário inexistente, senha errada e conta bloqueada por tentativas |
| `test_tokens_do_provedor.py` | O perfil vai só no token de acesso, não no token de id nem no userinfo |
| `test_sessao.py` | O realm e o frontend usam os mesmos 30 minutos de inatividade |
| `test_tokens_visuais.py` | O tema de login repete os tokens visuais do frontend sem divergir |
| `test_origem_do_frontend.py` | A API só aceita chamadas do navegador vindas do frontend (CORS) |

## 7. A integração contínua roda em um pull request

Todo pull request para `homolog` ou `main` roda dois checks: **Estilo e testes** (`ruff`, subida do ambiente com o Keycloak e a suíte completa) e **Frontend (tipos, lint e build)**. Para ver, abra qualquer pull request da entrega, por exemplo o #24, e confira os checks na aba **Checks**.

## Encerrar

```
docker compose down -v
```
