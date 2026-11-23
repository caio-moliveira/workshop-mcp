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
├── keycloak/realm/   # configuração versionada do provedor de identidade
├── docs/             # PRDs, roadmap e ADRs
└── GLOSSARY.md       # termos do domínio
```

## Pré-requisitos

- Docker com Docker Compose
- [uv](https://docs.astral.sh/uv/), para rodar os testes

## Subir o ambiente

Na primeira vez, crie a configuração de ambiente e troque a senha:

```
cp backend/.env.example backend/.env
```

Depois, na raiz do projeto:

```
docker compose up -d --build --wait
```

O comando sobe o Postgres, roda a carga (que recria o banco do zero), sobe o Keycloak com o realm importado e, por último, a API. Ele só termina quando tudo está pronto, e termina com código diferente de zero se algo falhar, inclusive a carga.

| Serviço | Endereço local | Porta configurável por |
| --- | --- | --- |
| Postgres | `127.0.0.1:5433` | `POSTGRES_PORT` |
| Keycloak | `http://localhost:8080` | (fixa: é o emissor dos tokens) |
| API | `http://127.0.0.1:8000` | `API_PORT` |

Todos ficam presos à máquina local.

## Provedor de identidade

O Keycloak não guarda estado: a cada subida, importa `keycloak/realm/pulso.json` (ADR 0004). Mudanças no realm são feitas nesse arquivo, não no console. Reiniciar o Keycloak encerra as sessões.

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
