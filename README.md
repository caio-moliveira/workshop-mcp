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
│   ├── assistente/   # assistente da aplicação: agente (PydanticAI) que usa as ferramentas do servidor MCP
│   ├── aceite/       # a forma do resultado da execução de aceite, que a API lê para o painel de segurança
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

Para usar o assistente, preencha também `ANTHROPIC_API_KEY` (seção Assistente); sem ela, o resto do ambiente funciona igual.

Depois, na raiz do projeto:

```
docker compose up -d --build --wait
```

O comando sobe o Postgres, roda a carga (que recria o banco do zero), sobe o Keycloak com o realm importado, a API, o servidor MCP, o proxy reverso e, por último, o frontend. Ele só termina quando tudo está pronto, e termina com código diferente de zero se algo falhar, inclusive a carga.

| Serviço | Endereço local | Porta configurável por |
| --- | --- | --- |
| Postgres | `127.0.0.1:5433` | `POSTGRES_PORT` |
| Keycloak | `http://localhost:8080` | (fixa: é o emissor dos tokens) |
| API | `http://127.0.0.1:8000` | `API_PORT` |
| Servidor MCP | `http://127.0.0.1:8001/mcp` | `MCP_PORT` |
| Frontend | `http://localhost:5173` | (fixa: é o retorno do login, `ENDERECO_DO_FRONTEND`) |
| Proxy reverso (provedor e servidor MCP num endereço só) | `http://127.0.0.1:8088` | `PROXY_PORT` |

Todos ficam presos à máquina local.

## Provedor de identidade

O Keycloak não guarda estado: a cada subida, importa `keycloak/realm/pulso.json` (ADR 0004). Mudanças no realm são feitas nesse arquivo, não no console. Reiniciar o Keycloak encerra as sessões.

A tela de login usa o tema `pulso`, em `keycloak/temas/pulso/login/`: herda os templates do tema `base` do Keycloak e troca a moldura (`template.ftl`), o estilo (`resources/css/pulso.css`, com os mesmos tokens de `frontend/src/estilos/tokens.css`) e os textos. Em modo de desenvolvimento o Keycloak não guarda temas em cache: uma mudança no tema aparece ao recarregar a tela.

Usuários de demonstração, um por perfil e dois em Vendas (para mostrar que um não vê o histórico do outro), com as senhas em `backend/.env`:

| Usuário | Nome | Perfil | Senha |
| --- | --- | --- | --- |
| `ana.vendas` | Ana Ribeiro | Vendas | `SENHA_DO_USUARIO_VENDAS` |
| `vitor.vendas` | Vitor Nunes | Vendas | `SENHA_DO_USUARIO_VENDAS_VITOR` |
| `bruno.produtos` | Bruno Costa | Produtos | `SENHA_DO_USUARIO_PRODUTOS` |
| `carla.comercial` | Carla Mendes | Comercial | `SENHA_DO_USUARIO_COMERCIAL` |
| `diego.diretoria` | Diego Almeida | Diretoria | `SENHA_DO_USUARIO_DIRETORIA` |

O perfil vem do grupo do usuário no realm e viaja no token como a claim `perfil`.

## API

- `GET /eu`: o nome e o perfil do usuário do token. Qualquer problema com o token (ausente, vencido, de outro serviço, assinatura, emissor, perfil) recebe `401` com a mesma resposta; o motivo fica só no log da API.
- `GET /vendas/indicadores`, `/vendas/evolucao`, `/vendas/situacao-das-entregas` e `/vendas/pedidos-recentes`: os blocos do painel de Vendas, com `?periodo=` (`30d`, `90d`, `12m` ou `24m`; padrão `12m`).
- `GET /produtos/indicadores`, `/produtos/notas`, `/produtos/categorias`, `/produtos/mal-avaliados` e `/produtos/avaliacoes`: os blocos do painel de Produtos, com o mesmo `?periodo=` e nenhum outro parâmetro. O catálogo não depende do período; o período filtra pela data da avaliação. A rota das avaliações devolve as 20 mais recentes, com o comentário e o `aviso` de que ele é texto de clientes (ADR 0010).
- `GET /comercial/indicadores`, `/comercial/funil`, `/comercial/canais` e `/comercial/leads`: os blocos do painel do Comercial, com o mesmo `?periodo=` e nenhum outro parâmetro. Cada número usa a data do próprio fato: leads, funil, principal canal e leads recentes pela data de criação; novos lojistas e dias até fechar pela data de fechamento. A conversão é novos lojistas do período divididos pelos leads criados no mesmo período (veja `GLOSSARY.md`). A rota dos canais devolve os cinco canais da maior conversão para a menor; a dos leads, os 20 mais recentes, sem filtro de canal nem de etapa.
- `GET /diretoria/indicadores`, `/diretoria/tendencia`, `/diretoria/fatores-de-recompra` e `/diretoria/resumo`: os blocos do painel da Diretoria, com o mesmo `?periodo=` e nenhum outro parâmetro. Só indicadores consolidados, nunca um cliente, pedido, lead, avaliação, lojista ou produto (RF-04): a receita, a taxa de recompra, a satisfação e a retenção do período e do anterior, com as contagens de cada uma; a tendência de receita, taxa de recompra, satisfação e taxa de atraso por dia, semana ou mês; os fatores de recompra em três blocos (pela primeira entrega, pela primeira nota e a satisfação pela faixa de atraso), com o tamanho de cada grupo; e o resumo por canal do lojista, do canal que mais atrasa para o que menos atrasa. A receita é a mesma de Vendas, e a satisfação, a nota média de Produtos (veja `GLOSSARY.md`). A retenção não existe em 24 meses.
- Cada rota de dados só responde ao perfil dono; os outros perfis recebem `403 {"erro": "Acesso negado."}`, a mesma negação em toda rota, antes de o parâmetro ser validado (RF-11).
- `POST /assistente`: uma pergunta ao assistente. Veja a seção Assistente.
- `GET /conversas`, `GET /conversas/{id}` e `DELETE /conversas/{id}`: o histórico do assistente, só do próprio usuário. Veja a seção Assistente.
- `GET /seguranca`: a última execução de aceite, para o painel de segurança, igual para os quatro perfis. Só existe com o interruptor de demonstração ligado. Veja a seção Painel de segurança.

## Servidor MCP

O serviço `mcp` do compose expõe as consultas de Vendas, de Produtos, do Comercial e da Diretoria como ferramentas MCP, somente leitura, em `http://127.0.0.1:8001/mcp` (transporte streamable HTTP, sem sessão). Ele usa o mesmo módulo de acesso e o mesmo mecanismo de consultas da API (`backend/acesso` e `backend/consultas`), sem chamar a API.

- **Ferramentas**, declaradas em `backend/servidor_mcp/ferramentas.py`:
  - do perfil Vendas: `vendas_indicadores`, `vendas_evolucao`, `vendas_situacao_das_entregas`, `vendas_pedidos_recentes` e `vendas_atrasos`;
  - do perfil Produtos: `produtos_indicadores`, `produtos_notas`, `produtos_categorias`, `produtos_mal_avaliados` e `produtos_avaliacoes`. Todas recebem `periodo`; `produtos_avaliacoes` recebe também `produto`, opcional, o identificador do produto (inteiro positivo; um produto que não existe dá lista vazia);
  - do perfil Comercial: `comercial_indicadores`, `comercial_funil`, `comercial_canais` e `comercial_leads`. Todas recebem `periodo`; `comercial_leads` recebe também `canal` e `etapa`, opcionais, de enumeração fechada com os valores do glossário (um valor fora dela, inclusive sem acento, é parâmetro inválido; um recorte sem leads dá lista vazia). A empresa do lead vai ao modelo sem marcação: é texto gerado, não escrito por clientes (ADR 0010);
  - do perfil Diretoria: `diretoria_indicadores`, `diretoria_tendencia`, `diretoria_fatores_de_recompra` e `diretoria_resumo`. Todas recebem só `periodo`; qualquer outro campo é parâmetro inválido. As descrições dizem como cada indicador é calculado, que a taxa de recompra é maior em períodos curtos e quais grupos os fatores deixam de fora. Nenhum resultado traz texto livre dos dados.

  Cada perfil só lista as próprias ferramentas; nenhum perfil recebe a lista vazia. Uma chamada a uma ferramenta de outro perfil recebe o mesmo erro de uma ferramenta inexistente.
- **Conteúdo não confiável:** o comentário das avaliações é texto escrito por clientes. A descrição de `produtos_avaliacoes` e o campo `aviso` do resultado dizem que ele é dado, não instrução; o texto vai inteiro, cortado só em 500 caracteres, sem filtro nem detecção de texto suspeito (ADR 0010).
- **Token:** só aceita tokens do realm cujo destinatário inclui `pulso-mcp`. O token da aplicação (`pulso-web`) traz `pulso-api` e `pulso-mcp` (ADR 0006); o do cliente `pulso-inspector`, só `pulso-mcp`. Sem token ou com token recusado: `401`, com o `WWW-Authenticate` apontando os metadados de recurso protegido em `/.well-known/oauth-protected-resource/mcp`.
- **Endereço público:** `ENDERECO_PUBLICO_DO_MCP` no `backend/.env` (sem o `/mcp`), o recurso anunciado nos metadados. Precisa ser o endereço digitado no cliente do protocolo MCP (o Inspector, um assistente externo).
- **Auditoria:** toda chamada de ferramenta vira uma linha na tabela `auditoria.chamada`, no banco `auditoria`, com usuário, perfil, ferramenta, parâmetros, resultado e horário. A recarga não a apaga, e só o papel dono a lê (ADR 0008).
- **Limite de frequência:** 30 chamadas por usuário por minuto; `LIMITE_DE_CHAMADAS_POR_USUARIO` e `JANELA_DO_LIMITE_EM_SEGUNDOS`, no shell que roda o compose, trocam os valores.
- **Saúde:** `GET /saude`, sem token.

Para conectar o [MCP Inspector](https://github.com/modelcontextprotocol/inspector), use o cliente `pulso-inspector` do realm; o passo a passo está em `docs/demonstracao/entrega-4a.md`. Para colar um token sem passar pela tela de login, emita um de um usuário de demonstração, dentro de `backend/`:

```
uv run python -m token_de_demonstracao ana.vendas pulso-inspector
```

O comando imprime só o token de acesso, que vale 5 minutos. As aplicações são `pulso-web`, `pulso-inspector` e `pulso-outra-aplicacao` (um cliente que existe para provar que um token de outra aplicação é recusado).

## Assistente

O botão **Assistente**, na barra superior do frontend, abre um painel lateral em que o usuário pergunta em linguagem natural e vê a resposta chegar aos poucos. No desktop, **Expandir o assistente** troca o painel por uma área central de leitura, com a lista de conversas à esquerda; abaixo de 768 px o painel ocupa a tela inteira e o botão **Conversas** mostra a lista. As respostas podem ter subtítulos e tabelas. O agente mora na API (`backend/assistente`, com PydanticAI) e só obtém dados pelas ferramentas do servidor MCP: a cada pergunta, a API abre uma conexão nova com o servidor MCP pela rede interna e repassa o token de quem perguntou (RF-15). Por isso cada chamada aparece na auditoria com o usuário logado, conta no limite de frequência dele e só enxerga as ferramentas do perfil dele. A rota não tem regra de perfil própria, e a API não tem credencial própria para o servidor MCP.

- **Rota:** `POST /assistente`, com o token da aplicação (destinatário `pulso-api`). Corpo: `{"pergunta": "...", "id_da_conversa": "..."}`, com o identificador opcional: sem ele, nasce uma conversa nova, com o começo da pergunta como título; campos fora do previsto são recusados, entre eles a `conversa` reenviada da 5a. Antes da resposta, erros JSON no formato da API: `401` para token recusado, `400` para pergunta vazia ou acima dos tetos, `404` para conversa inexistente, de outro usuário ou com identificador fora do formato, `503` sem modelo, sem chave ou com o histórico fora do ar. Depois, um fluxo de eventos (SSE): `conversa` (o primeiro, com `id_da_conversa` e `id_da_pergunta`), `texto` (um trecho), `estado` (consultando os dados, sem nome de ferramenta), `chamada` (uma por chamada de ferramenta terminada, com `ferramenta`, `desfecho`, `concluida` ou `nao_concluida`, e `milissegundos`) e, no fim, exatamente um `fim` (com `aviso` quando o teto de chamadas foi atingido) ou um `erro` (sessão expirada, assistente indisponível ou tempo esgotado, sem nome interno). Se o cliente desconecta, a execução é cancelada.
- **Conversa:** gravada no banco `historico` (ADR 0009): a pergunta antes de o modelo ser chamado e a resposta ao terminar, em qualquer desfecho, com o texto emitido e a situação. A continuação lê do banco os pares de pergunta e resposta com texto, cada resposta junto da pergunta dela pelo identificador da pergunta, e entrega ao modelo os 20 itens mais recentes desses pares; o navegador não envia mais a conversa. `GET /conversas` lista as 50 conversas mais recentes do usuário, com título e última atividade; `GET /conversas/{id}` lê uma, com perguntas, respostas, situações e rastreio; `DELETE /conversas/{id}` a apaga de vez, sem tocar na auditoria. A conversa de outro usuário, do mesmo perfil ou de outro, recebe o mesmo `404` da inexistente (RF-18). O painel abre numa conversa nova a cada carga da página, e o navegador não guarda nada do histórico.
- **Rastreio:** cada resposta tem o bloco retrátil "Como esta resposta foi obtida", fechado por padrão: por chamada, a ferramenta pedida, se foi concluída e a duração, e o identificador da pergunta. Sem parâmetros nem texto de erro; uma chamada negada aparece como não concluída, com o nome pedido. O rastreio fica gravado com a resposta.
- **Pergunta sugerida:** Vendas, "O que está causando os atrasos?"; Produtos, "Quais categorias concentram as piores notas?"; Comercial, "Qual canal traz os leads que mais convertem?"; Diretoria, "Por que os clientes compram uma vez e não voltam?".
- **Log:** cada pergunta tem um identificador (UUID), que a API repassa ao servidor MCP num cabeçalho. Ele aparece em três linhas: a da pergunta, na API (início, fim e erro, com a conversa e o usuário); a de cada chamada, no servidor MCP; e a de cada consulta executada, com o nome e a duração (as consultas das telas saem "sem pergunta"). O texto da pergunta não vai para o log, e a auditoria não guarda o identificador. Para acompanhar uma pergunta: `docker compose logs api mcp | grep <identificador>`, com o identificador do bloco de rastreio.

Variáveis, no `backend/.env` (todas com padrão; veja `backend/.env.example`):

| Variável | Padrão | O que faz |
| --- | --- | --- |
| `MODELO_DO_ASSISTENTE` | `anthropic:claude-haiku-5-5` | O modelo, no formato `provedor:modelo` do PydanticAI. Trocar é mudar a linha e recriar só a API: `docker compose up -d --no-deps --wait api` (RF-16) |
| `ANTHROPIC_API_KEY` | vazia | A chave do provedor do modelo padrão, na variável que o provedor lê (outro provedor lê a própria). Vazia, o ambiente sobe normalmente, a rota responde 503 e o painel avisa que o assistente está indisponível |
| `LIMITE_DE_CHAMADAS_POR_PERGUNTA` | `8` | Chamadas de ferramenta por pergunta; ao atingir, a resposta termina com um aviso |
| `LIMITE_DE_CARACTERES_DA_PERGUNTA` | `2000` | Caracteres da pergunta; acima, 400 |
| `TEMPO_MAXIMO_DA_PERGUNTA_EM_SEGUNDOS` | `60` | Tempo máximo de uma pergunta; ao passar, a resposta termina com erro |
| `ENDERECO_INTERNO_DO_MCP` | `http://mcp:8001/mcp` | Onde a API chama o servidor MCP; o `compose.yaml` já o define para o serviço `api` |

A chave do provedor não vai para o repositório, para o log nem para as mensagens de erro. O passo a passo com o modelo real está em `docs/demonstracao/entrega-5a.md`; para o histórico, o rastreio e o modo expandido, em `docs/demonstracao/entrega-5b.md`; para Produtos, Comercial e Diretoria, em `docs/demonstracao/entrega-8.md`, `docs/demonstracao/entrega-9.md` e `docs/demonstracao/entrega-10.md`.

## Frontend

Abra `http://localhost:5173`. A aplicação leva ao login do Keycloak (fluxo de código com PKCE pelo cliente público `pulso-web`, ADR 0004), volta com o token só em memória e chama `GET /eu`; o nome e o perfil mostrados vêm dessa resposta. Recarregar a página volta sem pedir senha enquanto a sessão do provedor estiver ativa. O botão **Sair** encerra a sessão também no Keycloak.

**Painéis.** Cada perfil vê o próprio painel, com o filtro de período no endereço da página (`?periodo=`): Vendas (pedidos, receita, atrasos e aprovação; a evolução e a situação das entregas; os pedidos recentes), Produtos (Produtos no catálogo, nota média, produtos mal avaliados e avaliações recebidas; as avaliações por nota e as categorias com mais reclamações; os produtos mal avaliados e as avaliações recentes, com o comentário como texto simples) e Comercial (leads, novos lojistas, conversão e principal canal; os leads por etapa do funil, com Perdido separado, e os novos lojistas por canal, com a conversão na dica; o desempenho dos canais e os leads recentes) e Diretoria (receita, taxa de recompra, satisfação e retenção; a tendência dos quatro indicadores em gráficos pequenos lado a lado; os fatores de recompra em três blocos, com o tamanho do grupo na dica; o resumo por canal do lojista). As telas do Comercial e da Diretoria dizem "canal", nunca "origem", e a da Diretoria nunca mostra um lojista. As seis etapas do funil só aparecem preenchidas em 12 e 24 meses, porque a etapa de um lead não fechado depende da idade dele. Em 24 meses, a retenção da Diretoria mostra "—": não há período anterior nos dados.

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

`npm test` roda o Vitest nas funções puras: formatação, período da URL, variação, validação das respostas da API de Vendas, de Produtos, do Comercial, da Diretoria e do painel de segurança e, do assistente, a leitura do fluxo de eventos, o estado da conversa, a lista de conversas, o Markdown com tabelas, o painel (lateral e expandido), o teto de caracteres e a rede.

## Painel de segurança

O painel de segurança é a tela que mostra a última execução de aceite: os cenários de segurança, agrupados pela camada de defesa, com o resultado de cada um (permitido ou negado), a marca de divergência quando o resultado difere do esperado e os cartões-resumo (executados, permitidos, negados e divergências). Abra-o pelo item **Segurança** da barra lateral, em `http://localhost:5173/seguranca`, logado como qualquer um dos usuários de demonstração: a tela é igual para os quatro perfis.

**O comando.** A execução de aceite roda no terminal, contra o ambiente no ar, dentro de `backend/`:

```
uv run python tests/execucao_de_aceite.py
```

Ela mostra o andamento e o resumo e grava o resultado em `backend/execucao-de-aceite/ultima-execucao.json`, no lugar do anterior; a pasta não é versionada e o contêiner da API a monta só para leitura. Recarregue o painel para ver a nova execução. O comando termina com código 1 se algum cenário divergiu. O esperado de cada cenário vem dos registros de donos das rotas e das ferramentas; um resultado diferente é gravado como divergência, nunca escondido. Rode o comando a partir do checkout em que o compose foi subido: é a pasta dele que a API lê.

**A matriz completa.** Depois dos cenários, o mesmo comando percorre todos os pares de rotas e de ferramentas contra os quatro perfis, lidos dos registros de donos (hoje 17 rotas e 18 ferramentas, 140 pares): só o dono é permitido, e um par com resultado diferente do esperado, inclusive uma negação com outra resposta que não a genérica, conta como divergência e aparece no terminal. Os tokens são os dos cenários, e as ferramentas de cada perfil são chamadas numa sessão só do cliente MCP. Os cartões da matriz completa, no painel, mostram os pares executados, os permitidos, os negados e as divergências, para mostrar que os cenários da tela são uma amostra de uma verificação exaustiva. O comando termina com código 1 também se a matriz divergiu.

Tempo do comando, medido contra o compose com o servidor MCP no limite alto da suíte (entrega 11, ticket #108, com os cinco cenários da API): 24,4 s com a matriz completa e 13,3 s sem ela. A matriz em si leva cerca de 2,6 s; o resto da diferença é o login dos dois perfis que só ela usa, cerca de 4 s cada. Como cabe com folga nos 2 minutos, a matriz roda sempre, sem opção, e a data dela é a da própria execução. No limite padrão, de 30 chamadas por minuto, a matriz faz 18 chamadas por usuário: espere um minuto entre duas execuções seguidas, senão o limite barra as chamadas da segunda e elas aparecem como divergência.

**O interruptor de demonstração.** A variável `PAINEL_DE_SEGURANCA=ligado` liga o painel; o `compose.yaml` a define no serviço `api`, porque o ambiente local é o do workshop. Desligado, o padrão fora do compose, a rota `/seguranca` responde exatamente como uma rota inexistente (`404`), o `GET /eu` não diz nada sobre ela e o frontend não mostra o item **Segurança**.

**Ressalva.** O painel revela a qualquer usuário logado os nomes das rotas e das ferramentas de todos os perfis, o que o resto do projeto esconde de propósito (RF-11, RS-08). É um recurso de demonstração e não existiria em produção. Ele nunca mostra token, segredo nem dado de negócio: um cenário permitido traz só o status e a quantidade de linhas.

## Credenciais do banco

- `dono` (`POSTGRES_USER`): usado pela carga; recria o banco inteiro.
- `vendas` (`SENHA_DO_PAPEL_VENDAS`): lê apenas o esquema `vendas`, a camada de leitura do perfil Vendas, e é recusado nos dados de origem e nas camadas de leitura de Produtos, do Comercial e da Diretoria (ADR 0002).
- `produtos` (`SENHA_DO_PAPEL_PRODUTOS`): lê apenas o esquema `produtos`, a camada de leitura do perfil Produtos (produto, avaliação e data de referência, sem cliente, pedido, entrega, receita nem lojista), e é recusado nos dados de origem e nas camadas de leitura de Vendas, do Comercial e da Diretoria. Não escreve em nada e não se conecta aos bancos `auditoria` e `historico`.
- `comercial` (`SENHA_DO_PAPEL_COMERCIAL`): lê apenas o esquema `comercial`, a camada de leitura do perfil Comercial (o lead, com identificador, empresa, canal, etapa, data de criação e data de fechamento, e a data de referência; sem e-mail de contato, identificador do lojista, CNPJ, cidade, UF, pedido, entrega, receita, produto nem avaliação), e é recusado nos dados de origem e nas camadas de leitura de Vendas, de Produtos e da Diretoria. Não escreve em nada e não se conecta aos bancos `auditoria` e `historico`.
- `diretoria` (`SENHA_DO_PAPEL_DIRETORIA`): lê apenas o esquema `diretoria`, a camada de leitura da Diretoria, já agregada, uma linha por grupo, com o período como coluna (ADR 0011): os indicadores, a tendência, os fatores de recompra, o resumo por canal e a data de referência, cada linha com a contagem do grupo; nenhuma linha de cliente, pedido, lead, avaliação, lojista ou produto, e nenhum identificador, nome, e-mail, documento, endereço, cidade, UF ou comentário. É a única camada que cruza as três áreas. É recusado nos dados de origem e nas camadas de leitura de Vendas, de Produtos e do Comercial, e os papéis delas são recusados na dele. Não escreve em nada e não se conecta aos bancos `auditoria` e `historico`.
- `auditoria` (`SENHA_DO_PAPEL_AUDITORIA`): usado pelo servidor MCP; só insere na tabela da auditoria, sem ler, alterar nem apagar (ADR 0008).
- `historico` (`SENHA_DO_PAPEL_HISTORICO`): usado só pela API; lê, grava e apaga as conversas no banco `historico` e não se conecta a nenhum outro banco (ADR 0009).

As senhas ficam em `backend/.env`, que não é versionado. **Quem já tem o ambiente no ar de antes da entrega 8** precisa acrescentar `SENHA_DO_PAPEL_PRODUTOS` ao `backend/.env` (veja `backend/.env.example`) e refazer a carga (`docker compose run --rm --build carga`), que cria o papel e a camada de leitura de Produtos; sem a senha, o perfil Produtos é negado em toda consulta. **Quem já tem o ambiente no ar de antes da entrega 9** faz o mesmo com `SENHA_DO_PAPEL_COMERCIAL`: acrescenta a linha ao `backend/.env` e refaz a carga, que cria o papel e a camada de leitura do Comercial; sem a senha, o perfil Comercial é negado em toda consulta. **Quem já tem o ambiente no ar de antes da entrega 10** faz o mesmo com `SENHA_DO_PAPEL_DIRETORIA`: acrescenta a linha ao `backend/.env` e refaz a carga, que cria o papel e a camada de leitura da Diretoria; sem a senha, o perfil Diretoria é negado em toda consulta.

A API lê o banco só pelo mecanismo de consultas (`backend/consultas`): cada consulta declara um perfil, e o executor conecta com o papel desse perfil (`SENHA_DO_PAPEL_<PERFIL>`). Um perfil sem senha configurada é negado em toda consulta.

## Recarga

A recarga roda só a carga, que derruba o banco e o recria (ADR 0001). Os outros serviços continuam no ar, e os bancos `auditoria` e `historico` ficam como estavam; só `docker compose down -v` os apaga.

```
docker compose run --rm --build carga
```

## Testes

O servidor MCP do compose precisa estar com o limite de frequência alto: a suíte faz centenas de chamadas com o mesmo usuário, e o limite padrão (30 por minuto) as barraria. O limite de verdade é testado com o servidor criado dentro do processo. Na raiz do projeto:

```
LIMITE_DE_CHAMADAS_POR_USUARIO=100000 docker compose up -d --wait mcp
```

Sem isso, a suíte para logo no começo e avisa. Para voltar ao limite da demonstração, suba o `mcp` de novo sem a variável.

Com o ambiente no ar, dentro de `backend/`:

```
uv sync --locked
uv run pytest
uv run ruff check
uv run ruff format --check
```

Os testes rodam contra o Postgres e o Keycloak reais, sem mocks. Os da API criam a aplicação dentro do processo e obtêm tokens pelo mesmo fluxo de login do navegador (código + PKCE). Os do servidor MCP falam o protocolo MCP por HTTP, contra o serviço `mcp` do compose ou contra o servidor criado dentro do processo; por isso o ambiente inteiro, com o serviço `mcp`, precisa estar no ar.

A suíte leva cerca de 30 minutos, recarrega o banco e reinicia o Keycloak. O ambiente de testes é um compose por máquina: não rode duas suítes ao mesmo tempo.

## Demonstração

Os roteiros, com comandos e resultados esperados, estão em `docs/demonstracao/`:

- Entrega 1, fundação de dados: `docs/demonstracao/entrega-1.md`.
- Entrega 2, login e perfil: `docs/demonstracao/entrega-2.md`.
- Entrega 3, Vendas na tela: `docs/demonstracao/entrega-3.md`.
- Entrega 4a, servidor MCP de Vendas: `docs/demonstracao/entrega-4a.md`.
- Entrega 4b, auditoria e limite de frequência: `docs/demonstracao/entrega-4b.md`.
- Entrega 5a, chat de Vendas no painel lateral: `docs/demonstracao/entrega-5a.md`.
- Entrega 5b, chat expandido, rastreio e histórico: `docs/demonstracao/entrega-5b.md`.
- Entrega 8, perfil Produtos: `docs/demonstracao/entrega-8.md`.
- Entrega 9, perfil Comercial: `docs/demonstracao/entrega-9.md`.
- Entrega 10, perfil Diretoria: `docs/demonstracao/entrega-10.md`.

## Parar o ambiente

```
docker compose down -v
```
