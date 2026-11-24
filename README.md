# workshop-mcp

Consulta de dados por perfil com servidor MCP. Os requisitos estão em `docs/PRD.md` e a ordem das entregas em `docs/ROADMAP.md`.

## Estrutura

```
/
├── compose.yaml      # ambiente completo em contêineres
├── backend/          # projeto Python (uv)
│   ├── carga/        # recria o banco a partir do nada
│   ├── acesso/       # valida o token e extrai o perfil (compartilhado pela API e pelo servidor MCP)
│   ├── consultas/    # lê o banco com o papel do perfil (compartilhado pela API e pelo servidor MCP)
│   ├── api/          # API das telas (FastAPI)
│   ├── servidor_mcp/ # servidor MCP: as consultas como ferramentas (FastMCP)
│   └── tests/
├── frontend/         # aplicação no navegador (React + TypeScript + Vite), servida por nginx
├── keycloak/realm/   # configuração versionada do provedor de identidade
├── keycloak/temas/   # tema da tela de login (FE §9)
├── docs/             # PRDs, roadmap e ADRs
└── GLOSSARY.md       # termos do domínio
```

## Pré-requisitos

- Docker com Docker Compose
- [uv](https://docs.astral.sh/uv/), para rodar os testes
- Node.js 24, para desenvolver o frontend fora do contêiner e para o MCP Inspector (a versão 2.16 pede `^24.22.1`, `^22.23.4` ou `>=26.12.1`)

## Subir o ambiente

Na primeira vez, crie a configuração de ambiente e troque a senha:

```
cp backend/.env.example backend/.env
```

Depois, na raiz do projeto:

```
docker compose up -d --build --wait
```

O comando sobe o Postgres, roda a carga (que recria o banco do zero), sobe o Keycloak com o realm importado, a API, o servidor MCP e, por último, o frontend. Ele só termina quando tudo está pronto, e termina com código diferente de zero se algo falhar, inclusive a carga.

| Serviço | Endereço local | Porta configurável por |
| --- | --- | --- |
| Postgres | `127.0.0.1:5433` | `POSTGRES_PORT` |
| Keycloak | `http://localhost:8080` | (fixa: é o emissor dos tokens) |
| API | `http://127.0.0.1:8000` | `API_PORT` |
| Servidor MCP | `http://127.0.0.1:8001/mcp` | `MCP_PORT` |
| Frontend | `http://localhost:5173` | (fixa: é o retorno do login, `ENDERECO_DO_FRONTEND`) |

Todos ficam presos à máquina local.

## Provedor de identidade

O Keycloak não guarda estado: a cada subida, importa `keycloak/realm/pulso.json` (ADR 0004). Mudanças no realm são feitas nesse arquivo, não no console. Reiniciar o Keycloak encerra as sessões.

A tela de login usa o tema `pulso`, em `keycloak/temas/pulso/login/`: herda os templates do tema `base` do Keycloak e troca a moldura (`template.ftl`), o estilo (`resources/css/pulso.css`, com os mesmos tokens de `frontend/src/estilos/tokens.css`) e os textos. Em modo de desenvolvimento o Keycloak não guarda temas em cache: uma mudança no tema aparece ao recarregar a tela.

Usuários de demonstração, um por perfil, com as senhas em `backend/.env`:

| Usuário | Nome | Perfil | Senha |
| --- | --- | --- | --- |
| `ana.vendas` | Ana Ribeiro | Vendas | `SENHA_DO_USUARIO_VENDAS` |
| `bruno.produtos` | Bruno Costa | Produtos | `SENHA_DO_USUARIO_PRODUTOS` |
| `carla.comercial` | Carla Mendes | Comercial | `SENHA_DO_USUARIO_COMERCIAL` |
| `diego.diretoria` | Diego Almeida | Diretoria | `SENHA_DO_USUARIO_DIRETORIA` |

O perfil vem do grupo do usuário no realm e viaja no token como a claim `perfil`.

## API

- `GET /eu`: o nome e o perfil do usuário do token. Qualquer problema com o token (ausente, vencido, de outro serviço, assinatura, emissor, perfil) recebe `401` com a mesma resposta; o motivo fica só no log da API.

## Servidor MCP

O serviço `mcp` do compose expõe as consultas de Vendas como ferramentas MCP, somente leitura, em `http://127.0.0.1:8001/mcp` (transporte streamable HTTP, sem sessão). Ele usa o mesmo módulo de acesso e o mesmo mecanismo de consultas da API (`backend/acesso` e `backend/consultas`), sem chamar a API.

- **Ferramentas:** `vendas_indicadores`, `vendas_evolucao`, `vendas_situacao_das_entregas`, `vendas_pedidos_recentes` e `vendas_atrasos`, todas do perfil Vendas, declaradas em `backend/servidor_mcp/ferramentas.py`. Os outros perfis recebem a lista vazia, e uma chamada a uma ferramenta de outro perfil recebe o mesmo erro de uma ferramenta inexistente.
- **Token:** só aceita tokens do realm cujo destinatário inclui `pulso-mcp`. O token da aplicação (`pulso-web`) traz `pulso-api` e `pulso-mcp` (ADR 0006); o do cliente `pulso-inspector`, só `pulso-mcp`. Sem token ou com token recusado: `401`, com o `WWW-Authenticate` apontando os metadados de recurso protegido em `/.well-known/oauth-protected-resource/mcp`.
- **Endereço público:** `ENDERECO_PUBLICO_DO_MCP` no `backend/.env` (sem o `/mcp`), o recurso anunciado nos metadados. Precisa ser o endereço que o cliente MCP digita.
- **Saúde:** `GET /saude`, sem token.

Para conectar o [MCP Inspector](https://github.com/modelcontextprotocol/inspector), use o cliente `pulso-inspector` do realm; o passo a passo está em `docs/demonstracao/entrega-4a.md`. Para colar um token sem passar pela tela de login, emita um de um usuário de demonstração, dentro de `backend/`:

```
uv run python -m token_de_demonstracao ana.vendas pulso-inspector
```

O comando imprime só o token de acesso, que vale 5 minutos. As aplicações são `pulso-web`, `pulso-inspector` e `pulso-outra-aplicacao` (um cliente que existe para provar que um token de outra aplicação é recusado).

## Frontend

Abra `http://localhost:5173`. A aplicação leva ao login do Keycloak (fluxo de código com PKCE pelo cliente público `pulso-web`, ADR 0004), volta com o token só em memória e chama `GET /eu`; o nome e o perfil mostrados vêm dessa resposta. Recarregar a página volta sem pedir senha enquanto a sessão do provedor estiver ativa. O botão **Sair** encerra a sessão também no Keycloak.

**Inatividade.** A sessão termina depois de 30 minutos sem uso. O token só é renovado se o usuário interagiu com a página (ponteiro, teclado, rolagem ou volta à aba) desde a última renovação, porque cada renovação prorroga a sessão no Keycloak. Passados os 30 minutos sem interação, a aplicação encerra a sessão também no Keycloak e volta à tela de login. O valor vem de `INATIVIDADE_DA_SESSAO_EM_SEGUNDOS` no `compose.yaml`, que o realm e o `/configuracao.json` usam. Para encurtar numa demonstração, mantendo-o acima dos 5 minutos do token de acesso: `INATIVIDADE_DA_SESSAO_EM_SEGUNDOS=360 docker compose up -d --wait keycloak frontend`.

**Recusa da API.** Uma renovação que falha leva de volta ao login. Um `401` da API leva ao login só se a API já tinha aceitado um token nesta carga da página; se ela recusa de cara o token que o provedor acabou de emitir, entrar de novo não resolveria (o login voltaria em silêncio com outro token igual), e a aplicação mostra o erro com a ação **Sair**.

**Configuração.** O build não carrega endereço nenhum. O navegador busca `/configuracao.json` ao abrir a aplicação:

- No compose, o nginx monta esse arquivo ao subir o contêiner (`frontend/nginx/default.conf.template`), com `ENDERECO_PUBLICO_DO_PROVEDOR` do `backend/.env` e `ENDERECO_DA_API` do `compose.yaml`. Mudar um endereço pede só reiniciar o contêiner, sem rebuild.
- No servidor de desenvolvimento, o Vite serve o mesmo arquivo a partir do `backend/.env` (`frontend/vite.config.ts`).

A API só aceita chamadas do navegador vindas de `ENDERECO_DO_FRONTEND` (CORS).

**Desenvolvimento com recarga automática.** O servidor do Vite usa a mesma porta do contêiner, então pare o contêiner do frontend antes e deixe o resto do ambiente no ar:

```
docker compose stop frontend
cd frontend
npm ci
npm run dev
```

Checagens (as mesmas da CI):

```
npm run typecheck
npm run lint
npm test
npm run build
```

`npm test` roda o Vitest nas funções puras: formatação, período da URL, variação e validação das respostas da API.

## Credenciais do banco

- `dono` (`POSTGRES_USER`): usado pela carga; recria o banco inteiro.
- `vendas` (`SENHA_DO_PAPEL_VENDAS`): lê apenas o esquema `vendas`, a camada de leitura do perfil Vendas, e é recusado nos dados de origem (ADR 0002).

As senhas ficam em `backend/.env`, que não é versionado.

A API lê o banco só pelo mecanismo de consultas (`backend/consultas`): cada consulta declara um perfil, e o executor conecta com o papel desse perfil (`SENHA_DO_PAPEL_<PERFIL>`). Um perfil sem senha configurada é negado em toda consulta.

## Recarga

A recarga roda só a carga, que derruba o banco e o recria (ADR 0001). Os outros serviços continuam no ar.

```
docker compose run --rm --build carga
```

## Testes

Com o ambiente no ar, dentro de `backend/`:

```
uv sync --locked
uv run pytest
uv run ruff check
uv run ruff format --check
```

Os testes rodam contra o Postgres e o Keycloak reais, sem mocks. Os da API criam a aplicação dentro do processo e obtêm tokens pelo mesmo fluxo de login do navegador (código + PKCE). Os do servidor MCP falam o protocolo MCP por HTTP, contra o serviço `mcp` do compose ou contra o servidor criado dentro do processo; por isso o ambiente inteiro, com o serviço `mcp`, precisa estar no ar.

A suíte leva cerca de 11 minutos, recarrega o banco e reinicia o Keycloak. O ambiente de testes é um compose por máquina: não rode duas suítes ao mesmo tempo.

## Demonstração

Os roteiros, com comandos e resultados esperados, estão em `docs/demonstracao/`:

- Entrega 1, fundação de dados: `docs/demonstracao/entrega-1.md`.
- Entrega 2, login e perfil: `docs/demonstracao/entrega-2.md`.
- Entrega 3, Vendas na tela: `docs/demonstracao/entrega-3.md`.
- Entrega 4a, servidor MCP de Vendas: `docs/demonstracao/entrega-4a.md`.

## Parar o ambiente

```
docker compose down -v
```
