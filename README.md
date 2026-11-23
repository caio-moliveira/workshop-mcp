# workshop-mcp

Consulta de dados por perfil com servidor MCP. Os requisitos estão em `docs/PRD.md` e a ordem das entregas em `docs/ROADMAP.md`.

## Estrutura

```
/
├── compose.yaml      # ambiente completo em contêineres
├── backend/          # projeto Python (uv): carga do banco e testes
│   ├── carga/        # recria o banco a partir do nada
│   └── tests/
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
docker compose run --rm --build carga
```

O comando sobe o Postgres, espera ele ficar pronto e roda a carga, que recria o banco do zero. Ele termina com código diferente de zero se a carga falhar. O Postgres continua rodando, publicado só em `127.0.0.1:5433`; para usar outra porta, defina `POSTGRES_PORT` antes do comando.

## Recarga

A recarga é o mesmo comando da subida: ele derruba o banco e o recria (ADR 0001).

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

Os testes rodam contra o Postgres real, sem mocks.

## Parar o ambiente

```
docker compose down -v
```
