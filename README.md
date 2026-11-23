# workshop-mcp

Consulta de dados por perfil com servidor MCP. Os requisitos estão em `docs/PRD.md` e a ordem das entregas em `docs/ROADMAP.md`.

## Estrutura

```
/
├── compose.yaml      # ambiente completo em contêineres
├── backend/          # projeto Python (uv)
│   ├── carga/        # recria o banco a partir do nada
│   ├── acesso/       # valida o token e extrai o perfil (compartilhado com o futuro MCP)
│   ├── api/          # API das telas (FastAPI)
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
- Node.js 24, para desenvolver o frontend fora do contêiner

## Subir o ambiente

Na primeira vez, crie a configuração de ambiente e troque a senha:

```
cp backend/.env.example backend/.env
```

Depois, na raiz do projeto:

```
docker compose up -d --build --wait
```

O comando sobe o Postgres, roda a carga (que recria o banco do zero), sobe o Keycloak com o realm importado, a API e, por último, o frontend. Ele só termina quando tudo está pronto, e termina com código diferente de zero se algo falhar, inclusive a carga.

| Serviço | Endereço local | Porta configurável por |
| --- | --- | --- |
| Postgres | `127.0.0.1:5433` | `POSTGRES_PORT` |
| Keycloak | `http://localhost:8080` | (fixa: é o emissor dos tokens) |
| API | `http://127.0.0.1:8000` | `API_PORT` |
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

## Frontend

Abra `http://localhost:5173`. A aplicação leva ao login do Keycloak (fluxo de código com PKCE pelo cliente público `pulso-web`, ADR 0004), volta com o token só em memória e chama `GET /eu`; o nome e o perfil mostrados vêm dessa resposta. O token é renovado em silêncio antes de vencer, recarregar a página volta sem pedir senha enquanto a sessão do provedor estiver ativa, e uma renovação que falha ou um `401` da API levam de volta ao login. O botão **Sair** encerra a sessão também no Keycloak.

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
npm run build
```

## Credenciais do banco

- `dono` (`POSTGRES_USER`): usado pela carga; recria o banco inteiro.
- `vendas` (`SENHA_DO_PAPEL_VENDAS`): lê apenas o esquema `vendas`, a camada de leitura do perfil Vendas, e é recusado nos dados de origem (ADR 0002).

As senhas ficam em `backend/.env`, que não é versionado.

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

Os testes rodam contra o Postgres e o Keycloak reais, sem mocks. Os da API criam a aplicação dentro do processo e obtêm tokens pelo mesmo fluxo de login do navegador (código + PKCE).

## Demonstração

O roteiro da entrega 1, com comandos e resultados esperados, está em `docs/demonstracao/entrega-1.md`.

## Parar o ambiente

```
docker compose down -v
```
