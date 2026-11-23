# Roteiro de demonstração: entrega 1, fundação de dados

Este roteiro mostra a entrega 1 inteira, na ordem do roadmap. Cada passo traz o comando e o resultado esperado com a configuração padrão (semente 20261130, data de referência 30/11/2026). Os comandos são os mesmos no PowerShell e no bash e rodam na raiz do projeto, salvo quando o passo indica `backend/`.

Pré-requisitos: Docker com Docker Compose e [uv](https://docs.astral.sh/uv/).

## 1. Preparar a configuração

```
cp backend/.env.example backend/.env
```

O `backend/.env` guarda as senhas e não é versionado. Para a demonstração, os valores de exemplo bastam.

## 2. Subir do zero com um comando

```
docker compose run --rm --build carga
```

O comando sobe o Postgres, espera ele ficar pronto, recria o banco e carrega os dados. Resultado esperado, com código de saída 0:

```
carga: recriando o banco marketplace
carga: aplicando 001_esquemas.sql
...
carga: aplicando 006_avaliacoes.sql
carga: gerando dados com semente 20261130 e data de referência 2026-11-30
carga: impressão digital avaliacao d0e437fa52466e35e1e4cd53dc278895
carga: impressão digital categoria 7fafb07c119c07a56a5791d27fa45429
...
carga: impressão digital produto e2c6ffff3be5122178a879755cdea50d
carga: concluída
```

As linhas `impressão digital` são um hash por tabela dos dados de origem. Elas definem o que é "o mesmo banco".

## 3. Duas cargas produzem o mesmo banco

```
docker compose run --rm carga
```

Resultado esperado: as dez linhas `impressão digital` são idênticas às do passo 2. A suíte de testes também verifica isso, no passo 5.

## 4. Os dados terminam na data de referência, em qualquer dia

```
docker compose exec postgres psql -U dono -d marketplace -c "select min(momento_compra)::date as primeiro_pedido, max(momento_compra)::date as ultimo_pedido from dados_de_origem.pedido"
```

```
 primeiro_pedido | ultimo_pedido
-----------------+---------------
 2024-12-01      | 2026-11-30
```

A data de referência vem de `backend/carga/configuracao.toml`, não do relógio. Para mostrar que ela desloca a janela inteira, carregue com outra data e repita a consulta:

```
docker compose run --rm -e DATA_REFERENCIA=2025-11-30 carga
```

```
 primeiro_pedido | ultimo_pedido
-----------------+---------------
 2023-12-01      | 2025-11-30
```

Volte à configuração padrão antes de seguir:

```
docker compose run --rm carga
```

## 5. A suíte verifica padrões, volumes, datas e a avaliação maliciosa

Dentro de `backend/`:

```
uv sync --locked
uv run pytest
```

Resultado esperado: `87 passed`, em cerca de dois minutos. A suíte roda contra o Postgres real e recarrega o banco algumas vezes. O que cada arquivo verifica:

| Arquivo | O que verifica |
| --- | --- |
| `test_ambiente.py` | Subida, falha visível da carga, recarga, banco só em `127.0.0.1` |
| `test_determinismo.py` | Mesma impressão digital, data de referência, recarga depois de alterar dados |
| `test_comercial.py`, `test_catalogo.py` | Leads, canais, etapas do funil, lojistas, produtos, documentos fictícios |
| `test_vendas.py` | Clientes, pedidos, pagamentos, entregas e coerência das datas |
| `test_padroes_de_vendas.py` | Padrões 1, 2, 5 e 6 do PRD de dados |
| `test_avaliacoes.py` | Padrões 3 e 4 e a única avaliação maliciosa |
| `test_camada_vendas.py` | O que a credencial de Vendas lê e o que lhe é recusado |

## 6. A recarga devolve o estado inicial

Veja a impressão digital do banco como ele está, sem recarregar:

```
docker compose run --rm carga python -m carga.impressao_digital
```

Altere os dados como dono:

```
docker compose exec postgres psql -U dono -d marketplace -c "delete from dados_de_origem.avaliacao where nota = 1"
```

```
DELETE 1382
```

Repita o comando de impressão digital. A linha `avaliacao` muda, de `d0e437fa...` para outro valor. Então recarregue, com o mesmo comando da subida:

```
docker compose run --rm --build carga
```

Resultado esperado: as impressões digitais voltam a ser exatamente as do passo 2.

## 7. A credencial de Vendas lê só a própria camada

Conecte com o papel de Vendas. A senha é o valor de `SENHA_DO_PAPEL_VENDAS` em `backend/.env`:

```
docker compose exec postgres psql -h 127.0.0.1 -U vendas -d marketplace
```

Dentro do `psql`:

| Comando | Resultado esperado |
| --- | --- |
| `select count(*) from vendas.pedido;` | `29999` |
| `select * from dados_de_origem.cliente limit 1;` | `ERROR: permission denied for schema dados_de_origem` |
| `create temporary table t (id int);` | `ERROR: cannot execute CREATE TABLE in a read-only transaction` |
| `delete from vendas.pagamento;` | `ERROR: permission denied for view pagamento` |
| `begin read write; select lo_create(0);` | `ERROR: permission denied for function lo_create` |
| `\c postgres` | `FATAL: permission denied for database "postgres"` |

A sessão começa somente leitura, como mostra a primeira recusa, mas isso é só uma defesa extra. Quem barra a escrita são os privilégios, mesmo dentro de uma transação de escrita (ADR 0002).

## 8. A integração contínua roda em um pull request

Todo pull request para `homolog` ou `main` roda o check **Estilo e testes**: `ruff`, subida do ambiente e a suíte completa. As duas branches exigem esse check aprovado antes do merge, inclusive para administradores. Para ver, abra qualquer pull request da entrega, por exemplo o #14, e confira o check na aba **Checks**.

## Encerrar

```
docker compose down -v
```
