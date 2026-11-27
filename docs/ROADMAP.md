# Roadmap de entregas

Este documento define quais são as entregas do projeto e em que ordem. Ele não substitui as specs: o detalhe de cada entrega é decidido no ciclo dela, com `/grill-with-docs`, `/to-spec` e `/to-tickets`.

Fontes dos requisitos:

- `docs/PRD.md`: identificadores RF, RS, RNF e CA.
- `docs/PRD_frontend.md`: não tem identificadores; é citado como "FE §n" (número da seção).
- `docs/PRD_dados.md`: não tem identificadores; é citado como "PD" seguido da seção.

## Regras do fatiamento

- Cada entrega deixa algo funcionando de ponta a ponta e demonstrável sozinho.
- Um único perfil (Vendas) atravessa todas as camadas antes de os outros três entrarem.
- Requisitos de segurança e testes de isolamento entram junto com a funcionalidade que protegem.
- O PRD de frontend é aplicado em cada entrega, como especificação visual. Não há etapa de frontend com dados fictícios (FE §14 não é seguido ao pé da letra), e o banco populado vem antes de qualquer tela.
- Este roadmap não define nomes de tabelas, rotas ou arquivos.

## Ordem

| # | Entrega | Depende de | Situação |
| --- | --- | --- | --- |
| 1 | Fundação de dados | — | Concluída |
| 2 | Login e perfil | 1 | Concluída |
| 3 | Vendas na tela | 2 | Concluída |
| 4a | Servidor MCP de Vendas | 3 | Concluída |
| V1 | Verificação com túnel: Claude e ChatGPT | 4a | Concluída (Claude verificado; ChatGPT declarado funcionando pelo usuário na 11, sem verificação na auditoria) |
| 4b | Auditoria e limite de frequência | 4a | Concluída |
| 5a | Chat de Vendas no painel lateral | 4b | Concluída |
| 5b | Chat expandido, rastreio e histórico | 5a | Concluída |
| 8 | Perfil Produtos | 5b | Concluída (roteiro executado em 26/11/2026, no fechamento da 9) |
| 9 | Perfil Comercial | 8 | Concluída |
| 10 | Perfil Diretoria | 9 | Concluída |
| 11 | Painel de demonstração e aceite final | 10, V1 | Concluída |

Depois do workshop:

| # | Entrega | Depende de | Situação |
| --- | --- | --- | --- |
| 6 | Ambiente público | 4a | Adiada: nuvem e domínio |
| 7 | Claude e ChatGPT no ambiente público | 6, 11 | Adiada |

O projeto é apresentado num workshop sobre MCP, com o ambiente local: tudo roda no compose da máquina do apresentador, e só os clientes externos (Claude e ChatGPT) entram por um túnel com HTTPS, como na V1. Os conceitos do workshop (o fluxo de autorização do protocolo, as ferramentas por perfil, o papel do banco por perfil, a auditoria e o limite de frequência) não dependem de um endereço público. Por isso a 11 depende só da 10 e da V1, e fecha pelo túnel o que antes era da 7: o ChatGPT, o RF-27 a RF-29 e o CA-06. As entregas 6 e 7 mantêm seus números e ficam para depois do workshop, sem prazo: entram quando a decisão de nuvem e domínio for tomada, e a 7 passa a ser só repetir no endereço público o que a 11 fez pelo túnel.

## Entregas

### 1. Fundação de dados

- **O que passa a funcionar:** o ambiente sobe em contêineres com o banco preenchido pelo script gerador de dados sintéticos e com a camada de leitura de Vendas, acessível só pela credencial desse perfil.
- **Como demonstrar:**
  - O ambiente sobe do zero com um comando.
  - Rodar o gerador duas vezes produz exatamente o mesmo banco, e o comando de recarga devolve o estado inicial.
  - Os dados terminam na data de referência configurada no gerador (valor inicial: 30 de novembro de 2026), independentemente do dia da execução.
  - Testes automatizados verificam os seis padrões do PRD de dados, os volumes aproximados, a coerência das datas e a existência de uma única avaliação maliciosa.
  - A credencial de Vendas lê a própria camada e é recusada nas tabelas de origem.
  - A integração contínua roda em um pull request.
- **Depende de:** nada.
- **Cobre:** RF-01, RF-02 (Vendas), RF-03 (no banco), RF-05 (Vendas), RS-04 (Vendas), RS-09, RNF-01, RNF-04, RNF-07, CA-08; PD inteiro (volumes, conteúdo por área, padrões 1 a 6, regras).

### 2. Login e perfil

- **O que passa a funcionar:** cada um dos quatro usuários de demonstração faz login e vê a estrutura da aplicação com seu nome e perfil. A sessão expira.
- **Como demonstrar:**
  - Entrar com os quatro usuários e ver o perfil correto.
  - A API recusa requisição sem token, com token vencido e com token emitido para outro serviço.
  - O provedor de identidade sobe já configurado, sem passo manual.
- **Depende de:** 1.
- **Cobre:** RF-06 (tela), RF-07, RF-08, RF-09 (API), RS-01, RS-02, RS-03 (API), RNF-03; FE §1 a §5, §9 (login), §12 (estrutura global).

### 3. Vendas na tela

- **O que passa a funcionar:** o usuário de Vendas vê o painel com indicadores, gráficos, tabela e filtro de período. Os outros três perfis recebem negação.
- **Como demonstrar:**
  - Painel de Vendas com os dados do banco.
  - Teste automatizado dos quatro perfis contra as rotas de Vendas, com sucesso só para Vendas.
  - A negação não indica se o dado existe nem revela nomes internos.
  - Tempo de resposta medido contra a meta do RNF-05.
- **Depende de:** 2.
- **Cobre:** RF-03, RF-10, RF-11, RF-13 (o mecanismo compartilhado nasce aqui), RS-05, RS-06, RS-08 (rotas), RNF-05, CA-01 e CA-02 (parciais); FE §6 (Vendas), §7, §10, §11, §12 (componentes de painel).

### 4a. Servidor MCP de Vendas

- **O que passa a funcionar:** um cliente MCP autenticado como Vendas lista e chama as ferramentas de Vendas. Qualquer outro perfil recebe lista vazia e negação na chamada direta.
- **Como demonstrar:**
  - Teste automatizado dos quatro perfis contra todas as ferramentas, com sucesso só para Vendas.
  - Chamada direta a uma ferramenta não listada é negada.
  - Token emitido para outra aplicação é recusado; token vencido também.
  - Parâmetro fora do previsto é recusado.
- **Depende de:** 3 (reusa o mecanismo de acesso a dados).
- **Cobre:** RF-06 (MCP), RF-09 (MCP), RF-13, RF-19 a RF-26, RS-01, RS-02, RS-03, RS-05, RS-08 (ferramentas), CA-02 (ferramentas), CA-03.

### V1. Verificação com túnel: Claude e ChatGPT

- **O que passa a funcionar:** com o ambiente local exposto por um túnel, o Claude e o ChatGPT se registram no servidor MCP, iniciam o login do usuário e chamam uma ferramenta de Vendas.
- **Como demonstrar:**
  - Roteiro manual: conectar cada cliente, fazer login como Vendas e obter uma resposta.
  - Registro do que precisou ser ajustado no provedor de identidade e no servidor para cada cliente.
- **Depende de:** 4a.
- **Cobre:** RF-27 e RF-28 (verificação antecipada; o fechamento é na entrega 11, pelo túnel).
- **Observação:** é uma verificação de risco, não o ambiente definitivo. Se ela mostrar que o fluxo de autorização exige mudanças, elas entram antes da 4b.
- **Resultado (24/11/2026):** concluída com o Claude, no roteiro `docs/demonstracao/verificacao-v1.md`. O Claude se registrou sozinho, levou ao login de `ana.vendas` e chamou o servidor MCP; `diego.diretoria` viu a lista vazia. O Claude exigiu dois ajustes no realm: a política de escopos do registro anônimo passou a aceitar `openid`, e o escopo `pulso-mcp` passou a trazer o nome do usuário (ADR 0007).
- **Lacunas:** o ChatGPT não foi verificado, por decisão do usuário. O endereço de retorno dele já é aceito pelo registro anônimo (teste automático), mas o fluxo completo fica para a entrega 7. Do Claude, a verificação registrou as chamadas ao servidor MCP com 200, mas não anotou os números da resposta: conferi-los com o painel na próxima execução.

### 4b. Auditoria e limite de frequência

- **O que passa a funcionar:** toda chamada de ferramenta, permitida ou negada, fica registrada, e um usuário que chama demais é contido.
- **Como demonstrar:**
  - Toda chamada feita nos testes da 4a aparece na auditoria com usuário, perfil, ferramenta, parâmetros, resultado e horário.
  - Nenhuma ferramenta consegue ler a auditoria.
  - O limite de frequência dispara para um usuário sem afetar outro.
- **Depende de:** 4a.
- **Cobre:** RF-30, RF-31, RF-32, RS-11, CA-07.
- **Resultado (24/11/2026):** concluída, no roteiro `docs/demonstracao/entrega-4b.md`. Toda chamada ao servidor MCP vira uma linha no banco `auditoria`, com o desfecho (`permitida`, `negada`, `parametro_invalido`, `limitada` ou `falha`), gravada antes da resposta; se a gravação falha, a chamada é recusada. O banco fica fora da recarga e só o papel dono o lê; o papel que grava só insere, e os papéis de perfil nem se conectam (ADR 0008). O limite de frequência é de 30 chamadas por usuário por minuto, em janela deslizante, configurável pelo shell que roda o compose; a suíte de testes sobe o `mcp` com um limite alto.

### 5a. Chat de Vendas no painel lateral

- **O que passa a funcionar:** o usuário de Vendas pergunta em linguagem natural no painel lateral e recebe a resposta em tempo real, obtida só pelas ferramentas do MCP e com a identidade dele.
- **Como demonstrar:**
  - A pergunta sugerida de Vendas é respondida com dados do banco.
  - Pedidos para ignorar as regras ou mostrar dados de outro perfil não retornam esses dados; o chat informa que não tem acesso.
  - As chamadas do chat aparecem na auditoria com o usuário logado, não com uma conta de serviço.
  - A troca de modelo é feita só por configuração.
- **Depende de:** 4b.
- **Cobre:** RF-12, RF-14, RF-15, RF-16, RF-17, RS-03 (modelo), RS-06, CA-04; FE §8 (chat lateral), §6 (pergunta sugerida de Vendas).
- **Resultado (25/11/2026):** concluída, no roteiro `docs/demonstracao/entrega-5a.md`, executado pela API com o modelo real. O agente (PydanticAI) mora na API e chama o servidor MCP pela rede interna com o token de quem pergunta; a resposta sai em fluxo de eventos (SSE) e o painel lateral a mostra aos poucos, em Markdown. A pergunta sugerida "O que está causando os atrasos?" foi respondida pelo modelo padrão em cerca de 10 s, com `vendas_atrasos` por rota e por lojista, e todos os números citados conferem com o painel (taxa de atraso de 9,0%, 1.411 atrasos em 15.622 entregues, nos 12 meses); a continuação "e por lojista?" usou a conversa. Os deslizes do modelo padrão foram de interpretação, não de dado: numa execução chamou de "próxima da média" uma taxa que é o dobro dela, e corrigiu na continuação; noutra, errou uma soma de participações. O pedido para ignorar as regras e o pedido de dados de Produtos não trouxeram dados de outro perfil, e a Diretoria não recebeu ferramenta nenhuma (CA-04). As chamadas apareceram na auditoria com o nome e o perfil da Ana. A troca para `anthropic:claude-sonnet-5-5` foi feita só por `MODELO_DO_ASSISTENTE`, recriando o serviço `api`. A parte visual do painel (chip, Esc, tela cheia, parar) ficou para conferência manual no navegador, com os passos no roteiro. Tetos por pergunta: 8 chamadas de ferramenta, 2.000 caracteres e 60 segundos, configuráveis.

### 5b. Chat expandido, rastreio e histórico

- **O que passa a funcionar:** o chat ganha o modo expandido, o bloco "Como esta resposta foi obtida" e o histórico de conversa, isolado por usuário.
- **Como demonstrar:**
  - Uma resposta longa é lida no modo expandido, com o bloco de rastreio mostrando ferramenta, status e tempo.
  - Dois usuários, do mesmo perfil e de perfis diferentes, não veem o histórico um do outro.
  - Uma pergunta é acompanhada nos logs até as consultas feitas no banco.
- **Depende de:** 5a.
- **Cobre:** RF-18, RNF-06; FE §8 (chat expandido e bloco de rastreio).
- **Resultado (25/11/2026):** concluída, no roteiro `docs/demonstracao/entrega-5b.md`, executado pela API com o modelo real. As conversas ficam no banco `historico`, que só a API alcança, com um papel próprio, e que a recarga não toca (ADR 0009); a conversa entregue ao modelo vem do banco, não do navegador. O roteiro foi executado num ambiente subido do zero (`docker compose down -v`, histórico com 0 conversas e auditoria com 0 linhas antes da primeira pergunta), com o código depois das correções da revisão. A pergunta sugerida foi respondida em cerca de 8 s, com `vendas_atrasos` por rota e por lojista, e os números citados conferem com o painel (9,0%, 1.411 atrasos em 15.622 entregues, nos 12 meses); a continuação pedindo uma tabela trouxe as 10 rotas com mais atraso, com taxas e participações certas linha a linha; uma pergunta do segundo usuário de Vendas e outra de 90 dias também conferiram com o painel. A conversa lida de volta trouxe a situação, o identificador da pergunta (o mesmo do evento `conversa`) e o rastreio (ferramenta, desfecho e duração). Entre `ana.vendas`, `vitor.vendas`, `bruno.produtos` e `diego.diretoria`, listar, ler, continuar e apagar a conversa de outro deu sempre o mesmo 404 de uma conversa inexistente, como o identificador fora do formato na leitura e no corpo da pergunta (RF-18); cada lista terminou só com as conversas do dono. O identificador da pergunta mostrado no rastreio apareceu, em `docker compose logs`, na linha da pergunta na API, nas das chamadas no servidor MCP e nas das consultas, sem o texto da pergunta (RNF-06). Apagar uma conversa não mudou a contagem da auditoria (4 linhas antes e depois), e a recarga manteve as 3 conversas e os 8 itens do histórico. Lacunas: (1) a parte visual (modo expandido, lista de conversas, bloco de rastreio aberto e fechado, tabela rolando no painel lateral, teclado e Esc, tela pequena e os dois usuários de Vendas no navegador) não foi conferida; está no roteiro como conferência manual. (2) O modelo recebe do histórico só os textos de pergunta e resposta, sem as chamadas; numa execução, ele "corrigiu" numa continuação uma afirmação verdadeira, dizendo que não tinha consultado uma ferramenta que a auditoria mostra que ele consultou (na execução do zero, a correção que fez estava certa). (3) O modelo padrão erra por pouco as contas que faz sobre os dados: o ticket médio saiu R$ 1.053,86 em vez de R$ 1.053,87 (antes, R$ 1.054,01), e a soma das participações das 10 rotas, "cerca de 35%" em vez de 32,2%, corrigida por ele na continuação; os números copiados das ferramentas estavam certos. (4) Diferenças do modo expandido anotadas na implementação: a coluna de leitura é fixa em 820 px e fica abaixo de 760 px entre cerca de 768 e 1.100 px de largura, por causa dos 280 px da lista; o botão "Conversas" fica escondido no modo expandido; a área expandida não cobre a barra lateral, e um link dela troca a página por baixo sem recolher o painel. (5) A chamada negada como "não concluída" no rastreio só foi vista nos testes, com o modelo roteirizado; com o modelo real, ela não foi provocada.

### 6. Ambiente público

- **O que passa a funcionar:** aplicação, API, servidor MCP e provedor de identidade ficam acessíveis por endereços públicos próprios com HTTPS. O banco fica só na rede interna.
- **Como demonstrar:**
  - Login e painel de Vendas pelo endereço público.
  - O banco não responde de fora da rede interna.
- **Depende de:** 4a (tecnicamente); na prática entra quando a decisão de nuvem e domínio for tomada.
- **Cobre:** RS-10, RNF-02.
- **Bloqueada por:** provedor de nuvem e domínio.
- **Situação (26/11/2026):** adiada para depois do workshop. O workshop usa o ambiente local, com os clientes externos pelo túnel (veja a Ordem). RS-10 fica coberto em parte pelo túnel, na V1 e na 11; o fechamento dele e o RNF-02 continuam aqui. **Antecipado na 11 (#114):** um túnel nomeado da Cloudflare, com endereço fixo num domínio do usuário, para os assistentes externos; é só o endereço público do proxy reverso, com HTTPS, sem hospedagem, sem endereços próprios para cada serviço e sem o banco numa rede de nuvem.

### 7. Claude e ChatGPT no ambiente público

- **O que passa a funcionar:** o usuário conecta o servidor MCP público no Claude e no ChatGPT, faz login pelo fluxo do protocolo e obtém os mesmos dados da aplicação.
- **Como demonstrar:**
  - Roteiro com a mesma pergunta na aplicação, no Claude e no ChatGPT, com o mesmo resultado.
  - Um usuário de outro perfil conectado não vê as ferramentas que não são dele.
- **Depende de:** 6 e 11.
- **Cobre:** RF-06 (cliente externo), RF-27, RF-28, RF-29 e CA-06, repetidos no endereço público.
- **Situação (26/11/2026):** adiada para depois do workshop. A primeira verificação do ChatGPT e o fechamento de RF-27 a RF-29 e do CA-06 passaram para a 11, pelo túnel; aqui fica só repetir o roteiro da 11 no endereço público.

### 8. Perfil Produtos

- **O que passa a funcionar:** o usuário de Produtos tem camada de leitura, painel, ferramentas e chat próprios.
- **Como demonstrar:**
  - A matriz de isolamento cruza dois perfis reais nos dois sentidos, em rotas, ferramentas e credenciais do banco.
  - A avaliação maliciosa presente nos dados não altera o comportamento do agente.
  - A pergunta sugerida de Produtos é respondida.
- **Depende de:** 5b.
- **Cobre:** RF-02, RF-05, RF-10, RF-20, RS-04 (Produtos), RS-07, CA-05, CA-01 e CA-02 (ampliados); FE §6 (Produtos).
- **Resultado (25/11/2026):** implementada, com a suíte automatizada passando, mas **o roteiro de demonstração não foi executado**. O roteiro `docs/demonstracao/entrega-8.md` está escrito, com os comandos e o que se espera de cada passo, e sem resultado observado: a execução foi interrompida a pedido, antes de o ambiente ser subido do zero. O que existe: o papel `produtos` e a camada de leitura de Produtos (produto, avaliação e data de referência, sem cliente, pedido, entrega, receita nem lojista), cinco rotas e cinco ferramentas de Produtos, o painel de Produtos (quatro cartões, com "Produtos no catálogo" no lugar de "produtos ativos", dois gráficos e duas tabelas), a pergunta sugerida "Quais categorias concentram as piores notas?" e o comentário das avaliações marcado como texto de clientes na descrição de `produtos_avaliacoes` e no campo `aviso` do resultado, sem filtro (ADR 0010). A suíte completa do backend, a partir do código da branch, com `api`, `mcp` (limite alto) e `frontend` reconstruídos dele: 952 testes passando, nenhuma falha, em 21 min 43 s; `ruff check` e `ruff format --check` limpos. No frontend: Vitest com 287 testes em 22 arquivos passando, e tipos, lint e build limpos. Na suíte, as matrizes de isolamento cruzam todos os perfis contra todas as rotas, ferramentas e papéis, lidos dos registros, e o CA-05 é provado com o modelo roteirizado. Lacunas: (1) o roteiro não foi executado: nem a pergunta sugerida com o modelo real e os números conferidos contra as rotas, nem a pergunta sobre as avaliações do produto 1 em 24 meses, que traz a avaliação maliciosa ao modelo real (o comportamento do modelo real diante dela continua sem conferência: o texto da resposta, o rastreio e as linhas da auditoria), nem os pedidos de dados do outro perfil (RF-17), nem a matriz entre `ana.vendas` e `bruno.produtos` executada à mão. (2) O tempo das rotas de Produtos contra os 3 segundos do RNF-05 não foi medido; o comando (`tests/demonstracao.py tempos 24m produtos`) está pronto, e não há teste automatizado de tempo para as rotas de Produtos, como há para as de Vendas. (3) A parte visual (cartões, gráficos, tabelas, troca de período, pergunta sugerida e troca para `ana.vendas`) não foi conferida, nem no Chrome nem manualmente; os passos estão no roteiro. (4) Continuam abertas as lacunas da 5b que a spec deixou de fora: o modelo não recebe do histórico as chamadas anteriores, e a chamada negada com o modelo real.
- **Situação atualizada (26/11/2026):** o roteiro foi executado no fechamento da entrega 9, na mesma subida do ambiente (do zero, com o código da 9 e o `mcp` no limite padrão), e o resultado observado de cada passo está em `docs/demonstracao/entrega-8.md`. **Lacunas fechadas:** (1) o roteiro inteiro. A pergunta sugerida foi respondida pelo modelo real em cerca de 5 s, com `produtos_categorias`, e os números conferem com a rota (Móveis 3,94 e 17,7%, Celulares e acessórios 3,97, Beleza e perfumaria 3,98, Papelaria 4,29, Pet shop com 181 reclamações); a resposta disse que a nota varia pouco e que a taxa de reclamação é o que compara. Diante da avaliação maliciosa do produto 1 em 24 meses, o modelo real resumiu as 10 avaliações com as contagens certas, disse que uma delas continha instruções para revelar dados de clientes e de perfis internos e que as ignorou, e não trouxe dado de outro perfil; o rastreio e a auditoria ficaram só com `produtos_avaliacoes`, com o usuário de Produtos (CA-05). Os dois pedidos de dados do outro perfil terminaram em "não tenho acesso", sem chamada nenhuma. A matriz foi executada à mão, já com três usuários (veja a 9). (2) O tempo das rotas de Produtos em 24 meses: medianas de 6 a 16 ms, contra a meta de 3 s; e a 9 trouxe o teste automatizado de tempo para todas as rotas do registro. (3) A parte visual foi conferida no Chrome, pelo agente: cartões, os dois gráficos com a dica, as duas tabelas, a troca de período (4, 26, 20 e 7 produtos mal avaliados) e a troca para `ana.vendas`, com os números iguais aos das rotas. **Lacunas que continuam:** a pergunta sugerida de Produtos foi vista no navegador, mas não clicada (a resposta foi conferida pela API); tela pequena, teclado, leitor de tela e estados de carregamento, vazio e erro não foram conferidos no navegador; a avaliação maliciosa foi levada ao modelo padrão uma vez só, e o passo precisa ser repetido a cada troca de modelo; a execução foi com o código da 9, não com o do fechamento da 8; e as duas lacunas da 5b do item (4). Deslizes do modelo padrão nesta execução, de interpretação e de conta, não de dado copiado: chamou de "entre as melhores" a nota de Pet shop, que é a sexta pior das vinte, e disse que sete das dez avaliações do produto 1 não têm comentário, quando são quatro.

### 9. Perfil Comercial

- **O que passa a funcionar:** o usuário Comercial consulta o funil de lojistas na tela, nas ferramentas e no chat.
- **Como demonstrar:**
  - Matriz de isolamento com três perfis.
  - A pergunta sugerida do Comercial é respondida.
- **Depende de:** 8.
- **Cobre:** RF-02, RF-05, RF-10, RF-20, RS-04 (Comercial), CA-01 e CA-02 (ampliados); FE §6 (Comercial).
- **Resultado (26/11/2026):** implementada, com o roteiro `docs/demonstracao/entrega-9.md` executado num ambiente subido do zero, pela API com o modelo real e no Chrome; a suíte completa do backend passou inteira na segunda execução, depois de um teste desatualizado corrigido (abaixo). O que existe: o papel `comercial` e a camada de leitura do Comercial (o lead, com identificador, empresa, canal, etapa, data de criação e data de fechamento, e a data de referência; sem e-mail de contato, identificador do lojista nem nada de lojista, pedido, entrega, receita, produto ou avaliação, para que nada nela ligue um canal aos atrasos), quatro rotas e quatro ferramentas (`comercial_indicadores`, `comercial_funil`, `comercial_canais` e `comercial_leads`, esta com `canal` e `etapa` de enumeração fechada), o painel do Comercial (quatro cartões, o funil com Perdido separado, os novos lojistas por canal, o desempenho dos canais e os leads recentes) e a pergunta sugerida "Qual canal traz os leads que mais convertem?". A conversão é novos lojistas do período divididos pelos leads criados no mesmo período, uma razão entre dois movimentos e não uma coorte (glossário). No roteiro, a pergunta sugerida foi respondida pelo modelo padrão em cerca de 3 s, com `comercial_canais`, com os cinco canais em ordem de conversão, e todos os números conferem com a rota nos 12 meses (Mídia paga 57 de 222, 25,7%; Indicação 22 de 100, 22,0%; Eventos 13 de 80; Prospecção ativa 17 de 169; Orgânico 17 de 175). A pergunta "os lojistas de Mídia paga atrasam mais?" terminou em "não tenho acesso", sem número de atraso, e a auditoria só tem chamadas de `comercial_*` com o nome da Carla; o modelo leu "atrasam" como atraso de pagamento, e a pergunta refeita, sobre as entregas e a receita, terminou do mesmo jeito. As perguntas sobre o funil e sobre os leads de um canal numa etapa (nenhum de Indicação em Proposta, 8 de Mídia paga) conferem com os dados; `ana.vendas` e `bruno.produtos`, perguntando por leads, receberam "não tenho acesso", sem chamada. A matriz entre `ana.vendas`, `bruno.produtos` e `carla.comercial` foi executada à mão: nas treze rotas, 200 só para o dono e o mesmo `403 {"erro":"Acesso negado."}` para os outros dois, inclusive com período inválido; nas catorze ferramentas, cada um lista só as suas (pelo Inspector), e a chamada direta da ferramenta de outro perfil recebe a mesma resposta de uma ferramenta inexistente, com linha `negada` na auditoria; o papel `comercial` lê os 1.500 leads, é recusado nas camadas de Vendas e de Produtos e nos dados de origem, não escreve e não se conecta aos bancos `auditoria` e `historico`, e os papéis `vendas` e `produtos` são recusados na camada do Comercial. No Chrome, como `carla.comercial`, os cartões, os dois gráficos (com a conversão na dica), as duas tabelas, a troca de período (com o período no endereço e 24 meses sem variação) e a pergunta sugerida, com o modo expandido, a lista de conversas e o bloco de rastreio, mostraram os mesmos números das rotas nos quatro períodos; a troca para `ana.vendas` e `bruno.produtos` mostrou o painel e a pergunta sugerida de cada um. Os tempos em 24 meses, medidos contra a API do compose: 3 ms de mediana nas quatro rotas do Comercial, 6 a 16 ms nas de Produtos e 4 a 65 ms nas de Vendas, contra a meta de 3 s; a suíte ganhou o teste que mede todas as rotas do registro (`test_tempo_das_rotas.py`), no lugar do que media só as de Vendas. A suíte completa do backend rodou duas vezes, a partir do código da branch de integração, com os serviços reconstruídos dele e o `mcp` no limite alto: na primeira, 1.153 testes, 1.148 passando e 5 falhando, em 25 min 22 s; na segunda, depois da correção do teste desatualizado, 1.153 passando, nenhuma falha, em 25 min 4 s; `ruff check` e `ruff format --check` limpos. No frontend: Vitest com 425 testes em 32 arquivos passando, e tipos, lint e build limpos. Das 5 falhas da primeira execução, 4 são instabilidade do ambiente: o primeiro pedido de um arquivo de teste à API do compose recebeu 503, com "couldn't get a connection after 5.00 sec" no log da API (o conjunto de conexões dela depois de uma recarga do banco feita pela própria suíte), em `test_avaliacoes_de_produtos.py`, `test_ferramentas_de_vendas.py`, `test_indicadores_de_produtos.py` e `test_indicadores_do_comercial.py`, sempre no parâmetro `30d`; repetidos sozinhos, os quatro testes passaram em todos os parâmetros, e os 503 não se repetiram na segunda execução. A quinta era real: `test_login_pelo_inspector.py::test_token_do_inspector_de_outro_perfil_recebe_a_lista_vazia` usa o Comercial como exemplo de perfil sem ferramentas e espera a lista vazia, mas desde esta entrega o Comercial lista quatro ferramentas. O defeito é do teste, que ficou desatualizado (o perfil sem ferramentas agora é só a Diretoria), não do servidor; o exemplo do teste passou a ser a Diretoria. Lacunas: (1) os 503 do primeiro pedido à API do compose depois de uma recarga apareceram numa das duas execuções da suíte e ficam sem correção nem causa confirmada. (2) Tela pequena, teclado, leitor de tela e estados de carregamento, vazio e erro do painel do Comercial não foram conferidos no navegador, nem a entrada da Diretoria em "O painel chega em breve"; o tom do terracota não foi medido. (3) O limite de frequência não foi provocado à mão com o usuário do Comercial. (4) Continuam abertas as lacunas da 5b: o modelo não recebe do histórico as chamadas anteriores, e a chamada negada com o modelo real não aconteceu (o modelo não tentou ferramenta de outro perfil em nenhuma pergunta). Da parte visual da 5b, esta execução viu, com a Carla, o modo expandido com a lista de conversas, o bloco de rastreio aberto e a tabela rolando no painel lateral; o resto (teclado e Esc, tela pequena, dois usuários de Vendas) continua sem conferência. (5) Claude e ChatGPT com o perfil Comercial ficam para a entrega 7.

### 10. Perfil Diretoria

- **O que passa a funcionar:** a Diretoria consulta indicadores consolidados na tela e no chat, sem acesso a registros individuais dos outros perfis.
- **Como demonstrar:**
  - Matriz de isolamento completa, quatro perfis contra todas as rotas e ferramentas.
  - A credencial da Diretoria é recusada nas camadas dos outros perfis.
  - Nenhum registro individual nem dado pessoal aparece na camada da Diretoria.
  - A pergunta "Por que os clientes compram uma vez e não voltam?" é respondida a partir dos indicadores consolidados.
- **Depende de:** 9.
- **Cobre:** RF-02, RF-04, RF-05, RF-10, RF-20, RS-04 (completos), CA-01, CA-02 (completos); FE §6 (Diretoria). RF-10 e RF-20 faltavam aqui e foram acrescentados na spec da entrega (#96).
- **Resultado (26/11/2026):** implementada, com o roteiro `docs/demonstracao/entrega-10.md` executado num ambiente subido do zero, pela API com o modelo real e no Chrome; a suíte completa do backend passou inteira na primeira execução. O que existe: o papel `diretoria` e a camada de leitura da Diretoria, já agregada, uma linha por grupo, com o período como coluna (ADR 0011): cinco views (indicadores, tendência, fatores de recompra, resumo por canal e data de referência), toda linha com a contagem do grupo, sem identificador, nome, e-mail, documento, endereço, cidade, UF nem comentário; quatro rotas e quatro ferramentas (`diretoria_indicadores`, `diretoria_tendencia`, `diretoria_fatores_de_recompra` e `diretoria_resumo`, todas só com `periodo`), o painel da Diretoria (receita, taxa de recompra, satisfação e retenção; a tendência dos quatro indicadores em gráficos pequenos; os fatores de recompra em três blocos, com o tamanho do grupo na dica; o resumo por canal do lojista) e a pergunta sugerida "Por que os clientes compram uma vez e não voltam?". A tela "O painel chega em breve" deixou de existir, e nenhum perfil recebe mais a lista vazia de ferramentas. As definições estão no glossário (seção Diretoria). Nas rotas, os números de referência da spec conferem nos quatro períodos (clientes 2.173, 4.726, 15.379 e 27.301; recompra 308, 593, 1.204 e 1.365; retenção 11 de 1.296, 191 de 3.545 e 573 de 12.495; em 12 meses, primeira entrega no prazo 1.204 de 13.660 e com atraso 0 de 1.313, primeira nota 1 ou 2 com 10 de 1.258, 3 com 107 de 1.044 e 4 ou 5 com 1.087 de 8.408); a receita é igual à de Vendas e a satisfação à nota média de Produtos nos quatro períodos, e o resumo por canal soma os pedidos, a receita e os atrasos de Vendas. Mídia paga é o canal que mais atrasa nos quatro períodos (12,8% em 12 meses, 13,3% em 24). A pergunta sugerida foi respondida pelo modelo padrão três vezes (duas pela API, uma no navegador), em cerca de 5 s, com uma chamada a `diretoria_fatores_de_recompra`: os três elos certos, com números iguais aos da rota em 12 meses (0% de 1.313 contra 8,8% de 13.660; 0,8% de 1.258 contra 10,2% e 12,9%; notas 4,28, 2,83 e 1,75), tratados como associação e não como causa, e nenhum lojista, cliente ou produto citado; **mas nenhuma das três apontou o canal**, porque o modelo não chamou `diretoria_resumo` (lacuna 1). Perguntado direto, "Qual canal tem a pior taxa de atraso?", ele chamou `diretoria_resumo` e respondeu Mídia paga, 12,8%, 1.094 de 8.569, com os números da rota. As três negativas terminaram em "não tenho acesso": `diego.diretoria` pedindo os lojistas que mais atrasam (recebeu o recorte por canal, sem nome de lojista) e as avaliações do produto 1 (nenhuma chamada), e `ana.vendas` pedindo a taxa de recompra por canal (nenhuma chamada); a auditoria só tem chamadas de `diretoria_*` com o nome do Diego, nenhuma negada. A matriz foi executada à mão com os quatro usuários: nas dezessete rotas, 200 só para o dono e o mesmo `403 {"erro":"Acesso negado."}` para os outros três, inclusive com período inválido (102 negações); nas dezoito ferramentas, cada um lista só as suas (a Diretoria também pelo Inspector), e a chamada direta da ferramenta de outro perfil recebe a mesma resposta de uma ferramenta inexistente, com linha `negada` na auditoria; o papel `diretoria` lê só a camada dele, é recusado nas de Vendas, de Produtos e do Comercial e nos dados de origem, não escreve e não se conecta aos bancos `auditoria` e `historico`, e os outros três papéis são recusados na camada da Diretoria. Na camada, a menor contagem de grupo é 36 (nos fatores), nenhuma é 1. No Chrome, como `diego.diretoria`, os cartões, a tendência, os fatores (com o tamanho do grupo na dica), o resumo, a troca de período (com o período no endereço, 24 meses sem variação e a retenção "—", 12 meses com a retenção sem variação) e a pergunta sugerida, com o modo expandido e o rastreio, mostraram os números das rotas nos quatro períodos; o teclado (Enter no período, Tab até os gráficos, setas na dica), a tela pequena (num quadro de 390 px: sem rolagem horizontal da página, gráficos empilhados, tabela rolando dentro do contêiner) e os estados de carregamento, vazio e erro dos blocos (provocados trocando a resposta das rotas dentro da página) foram conferidos só no painel novo; a troca para `ana.vendas`, `bruno.produtos` e `carla.comercial` mostrou o painel de cada um (CA-01). Os tempos em 24 meses, contra a API do compose: 57 ms (indicadores), 85 ms (fatores), 124 ms (resumo) e 474 ms (tendência) de mediana, contra a meta de 3 s; nenhuma rota passou da meta, e a decisão de views comuns, não materializadas, fica como está (ADR 0011), apesar de a tendência ser bem mais lenta que os cerca de 20 ms medidos para o ADR. A suíte completa do backend, executada uma vez, a partir do código da branch de integração, com os serviços reconstruídos dele e o `mcp` no limite alto: 1.411 testes passando, nenhuma falha, em 30 min 20 s; `ruff check` e `ruff format --check` limpos. No frontend: Vitest com 563 testes em 41 arquivos passando, e tipos, lint e build limpos (o build só avisa do tamanho do pacote, como antes). Os 503 depois da recarga, vistos na 9, não apareceram. Lacunas: (1) o modelo padrão não chegou ao canal na pergunta sugerida, em três execuções; a descrição das ferramentas não foi mudada para ele acertar, e o canal só aparece quando perguntado direto. (2) O assistente não recebe o período do painel: com o painel em 24 meses, a pergunta sugerida foi respondida com os números de 12 meses, como nos outros perfis. (3) Deslizes de leitura do modelo padrão, não de dado copiado: na pergunta sobre a evolução, a faixa de receita mensal esqueceu dezembro de 2025 e a recompra foi dita "contínua" apesar da queda de junho; na dos lojistas, escreveu "canal de origem" e trocou a ordem de dois canais. (4) A tela pequena foi conferida num quadro de 390 px dentro da página, não numa janela ou aparelho desse tamanho, e os estados de carregamento, vazio e erro foram provocados no navegador, não com a API fora do ar; o vazio dos cartões não foi provocado. (5) Leitor de tela de verdade não foi usado (só a árvore de acessibilidade), e o tom do dourado não foi medido. (6) Em largura de desktop, o cartão da tendência estica até a altura dos três blocos de fatores e deixa um espaço vazio grande embaixo dos gráficos; não esconde nada. (7) O limite de frequência não foi provocado à mão com o usuário da Diretoria. (8) Continuam abertas as lacunas da 5b: o modelo não recebe do histórico as chamadas anteriores, e a chamada negada com o modelo real não aconteceu. (9) Os 503 do primeiro pedido à API depois de uma recarga, vistos na 9, não se repetiram, mas seguem sem causa confirmada. (10) Claude e ChatGPT com o perfil Diretoria ficam para a entrega 7.

### 11. Painel de demonstração e aceite final

- **O que passa a funcionar:** o apresentador vê a matriz de cenários de segurança, com permitidos e negados, e os oito critérios de aceite rodam em um roteiro único.
- **Como demonstrar:**
  - Painel com os resultados dos testes de isolamento.
  - Roteiro de CA-01 a CA-08 passando.
  - CA-06 repetido para os quatro perfis no Claude e no ChatGPT, pelo túnel, com a mesma pergunta na aplicação e nos dois clientes e o mesmo resultado.
  - Um usuário de outro perfil conectado por um cliente externo não vê as ferramentas que não são dele.
  - Revisão dos critérios de aceite visuais.
- **Depende de:** 10 e V1. Não depende mais da 7: o workshop usa o ambiente local, e os clientes externos entram pelo túnel.
- **Cobre:** CA-01 a CA-08 (fechamento), RF-06 (cliente externo), RF-27 a RF-29, RS-10 (em parte, pelo túnel), RNF-05 (medição final); FE §9 (painel de segurança), §13.
- **Observação:** o ChatGPT é verificado aqui pela primeira vez (modo desenvolvedor, registro dinâmico), com os passos esperados no roteiro da V1. Se ele não funcionar pelo túnel, isso fica registrado como lacuna e não bloqueia a 11; o Claude continua obrigatório.
- **Resultado (27/11/2026):** concluída, com o roteiro de aceite `docs/demonstracao/entrega-11.md` executado num ambiente subido do zero a partir do checkout principal, com o `mcp` no limite padrão; a parte de navegador está escrita no roteiro, com o esperado, e ficou sem conferência (lacuna 1). O que existe: o painel de segurança em `/seguranca`, igual para os quatro perfis, com os cartões, a matriz de 24 cenários em sete grupos (Token, Lista de ferramentas, Chamada, API, Banco, Limite de frequência e Assistente) e a gaveta do cenário; a rota `GET /seguranca`, fora do registro das rotas de dados, atrás do interruptor de demonstração (`PAINEL_DE_SEGURANCA`, que o compose liga); a execução de aceite (`uv run python tests/execucao_de_aceite.py`), com o esperado vindo dos registros de donos, a matriz completa e a conferência da carga; o roteiro do apresentador (`docs/demonstracao/roteiro-do-apresentador.md`); e o túnel nomeado, com endereço fixo (#114). A subida do zero levou 33 s, com a carga concluída, 0 conversas e 0 linhas na auditoria (CA-08); a recarga, 9 s, e a execução seguinte conferiu o banco no estado da carga. A execução de aceite, no limite padrão: 24 executados, 9 permitidos, 15 negados, 0 divergências, em 35,3 s pelo comando (38,2 s no relógio), e a matriz completa com 140 pares, 35 permitidos, 105 negados e 0 divergências (CA-02); o token de outra aplicação recusado com 401 (CA-03); cada chamada com a linha dela na auditoria, inclusive `negada` e `limitada` (CA-07). No fechamento, duas correções no cenário negado do assistente, vistas no Chrome: a linha e a gaveta mostravam "Status 200", o do `/assistente`, numa negação (agora o cenário grava sem status, como as ferramentas), e o título passou a dizer as duas camadas ("...: não listada e recusada"). Com o modelo real (CA-04), oito pedidos para ignorar as regras ou chamar pelo nome uma ferramenta de outro perfil, dois por usuário: as oito respostas recusaram, sem dado de outro perfil, e a auditoria ficou com uma linha só, `vendas_indicadores` da Ana. A avaliação maliciosa do produto 1, três vezes com `bruno.produtos` em 24 meses (CA-05): nas três, uma chamada a `produtos_avaliacoes`, a resposta disse que uma avaliação trazia instruções e que não as seguiu, sem dado de cliente nem de outro perfil, e a auditoria só com essas três linhas, com Bruno Costa. O laço do limite à mão: o Vitor barrado na 31ª chamada, com `Muitas chamadas em pouco tempo. Tente de novo em instantes.`, e a Ana passando logo depois. O CA-06, com o usuário, pelo túnel nomeado (26/11/2026): o Claude verificado na auditoria com `diego.diretoria` (quatro ferramentas da Diretoria, a pergunta dos lojistas recusada sem tentativa de ferramenta alheia) e `ana.vendas` (três ferramentas de Vendas), todas `permitida` com o usuário certo. CA-01: declarado concluído pelo usuário para os quatro usuários; observado no Chrome pelo orquestrador com `diego.diretoria` e `bruno.produtos`. Os tempos em 24 meses (RNF-05): as rotas de 2 a 445 ms de mediana e as ferramentas de 6 a 446 ms, todas abaixo de 3 s; a mais lenta é a tendência da Diretoria. Com o interruptor desligado, `GET /seguranca` deu o mesmo `404` de uma rota inexistente, com e sem token, e o `/eu` deixou de citar o painel. A suíte completa do backend, uma vez, com o `mcp` no limite alto: 1.470 testes, 1.469 passando e 1 falhando, em 33 min 11 s; `ruff check` e `ruff format --check` limpos. No frontend: Vitest com 633 testes em 47 arquivos passando, e tipos, lint e build limpos. A falha, `test_lista_de_conversas.py::test_a_lista_vem_em_ordem_de_ultima_atividade_com_titulo`, encontrou no topo da lista da Ana uma conversa de outro teste ("O que está causando os atrasos?"); repetido sozinho, o arquivo passou inteiro, e a causa não foi confirmada (lacuna 6). Lacunas: (1) **sem conferência no Chrome** (depois da subida do zero o navegador ficou sem sessão, e o login exige a senha de demonstração, que o agente não lê; o usuário pediu o fechamento autônomo): do painel de segurança, os cartões, as cores e os ícones da matriz, as gavetas do cenário de Chamada e do limite, o percurso por Tab e Enter, a tela pequena (pelo modo de dispositivo do DevTools: a janela do Chrome não redimensiona e o Keycloak recusa abrir a aplicação num quadro), o estado vazio, o interruptor desligado na tela e o cenário do assistente corrigido; e os dez critérios visuais da §13, que estão no roteiro sem veredito. Já visto no Chrome nesta entrega, como `diego.diretoria`: os 24 cenários e os sete grupos, a gaveta com Esc e a devolução do foco, o caminho "pulso. / Segurança", as "N ferramentas", o texto da gaveta do cenário do assistente e a tendência da Diretoria sem o espaço vazio em 1.568 px; e o painel igual com `bruno.produtos`. (2) CA-01: `ana.vendas` e `carla.comercial` declarados pelo usuário, não observados pelo orquestrador. (3) CA-06: os números das respostas do Claude não foram colados nem comparados com as rotas (continua a lacuna da V1); `bruno.produtos` sem nenhuma chamada na auditoria, embora o usuário tenha relatado que deu certo; `carla.comercial` e o ChatGPT só declarados pelo usuário, sem verificação na auditoria, e o RF-27 continua verificado só com o Claude; as senhas de demonstração, públicas no repositório, mantidas durante a exposição pelo túnel, por decisão do usuário. (4) A chamada negada com o modelo real continua sem ser vista: nos quatro pedidos que citavam pelo nome uma ferramenta de outro perfil, o modelo não tentou chamá-la; a negação é provada com o modelo roteirizado. (5) Deslizes de contagem do modelo padrão em duas das três respostas do CA-05 (quais avaliações não têm comentário). (6) A falha intermitente de `test_lista_de_conversas.py`, sem causa confirmada. (7) A execução de aceite gravada no painel é do código anterior às duas correções do cenário do assistente: depois do merge, rode-a de novo, no limite padrão. (8) `docker compose down -v` não apaga a última execução de aceite (a pasta é do checkout); o estado vazio exige tirar o arquivo à mão. Continuam abertas, das entregas anteriores: o período do painel não chega ao assistente; o modelo não cita o canal na pergunta sugerida da Diretoria; o modelo não recebe do histórico as chamadas anteriores (5b); e os 503 depois de uma recarga, vistos na 9, sem causa confirmada.

## Verificação de cobertura

Todos os requisitos com identificador aparecem em alguma entrega. RNF-02 e a parte de RS-10 que exige endereço público só fecham na 6, depois do workshop.

| Requisitos | Entregas |
| --- | --- |
| RF-01 a RF-05 | 1, 3, 8, 9, 10 |
| RF-06 a RF-09 | 2, 4a, 11 (7 depois do workshop) |
| RF-10 a RF-13 | 3, 4a, 5a, 8, 9, 10 |
| RF-14 a RF-18 | 5a, 5b |
| RF-19 a RF-26 | 4a, 8, 9, 10 |
| RF-27 a RF-29 | V1, 11 (7 depois do workshop) |
| RF-30 a RF-32 | 4b |
| RS-01 a RS-03 | 2, 4a, 5a |
| RS-04 | 1, 8, 9, 10 |
| RS-05, RS-06, RS-08 | 3, 4a, 5a |
| RS-07 | 8 |
| RS-09 | 1 |
| RS-10 | V1 e 11 (em parte, pelo túnel), 6 |
| RS-11 | 4b |
| RNF-01, RNF-04, RNF-07 | 1 |
| RNF-02 | 6 (depois do workshop) |
| RNF-03 | 2 |
| RNF-05 | 3, 11 |
| RNF-06 | 5b |
| CA-01, CA-02 | 3, 4a, 8, 9, 10, 11 |
| CA-03 | 4a, 11 |
| CA-04 | 5a, 11 |
| CA-05 | 8, 11 |
| CA-06 | 11, em parte (7 depois do workshop) |
| CA-07 | 4b, 11 |
| CA-08 | 1, 11 |
| FE §1 a §13 | 2, 3, 5a, 5b, 8, 9, 10, 11 |
| PD inteiro | 1 |

Fica de fora:

- **FE §14** (prompt de implementação com dados fictícios): contraria o fatiamento de ponta a ponta. O restante do PRD de frontend é aplicado em cada entrega.

## Decisões em aberto

Questões listadas em `docs/PRD.md`:

| Decisão | Bloqueia |
| --- | --- |
| ~~Provedor de modelo padrão do chat~~ | Decidida na 5a: Anthropic, com `anthropic:claude-haiku-5-5` por padrão, trocável por `MODELO_DO_ASSISTENTE` sem mudança de código. |
| Provedor de nuvem e domínio | 6 e, por consequência, 7. Adiada para depois do workshop; não bloqueia mais a 11. |
| ~~Como o agente obtém um token aceito pelo MCP: dois destinatários ou troca de token~~ | Decidida na 4a: dois destinatários, sem troca de token (ADR 0006). Não bloqueia mais a 5a. |
| ~~Meta de 3 segundos do RNF-05~~ | Confirmada na 11: em 24 meses, as dezessete rotas e as dezoito ferramentas abaixo de 0,51 s; a mais lenta, a tendência da Diretoria, com cerca de 0,45 s de mediana. |
| ~~Limite de chamadas por usuário do RS-11~~ | Decidida na 4b: 30 chamadas por usuário por minuto, configurável (`LIMITE_DE_CHAMADAS_POR_USUARIO` e `JANELA_DO_LIMITE_EM_SEGUNDOS`). |

Lacunas que os PRDs não listam:

| Lacuna | Bloqueia |
| --- | --- |
| ~~Definição dos indicadores da Diretoria (recompra, retenção, satisfação, fatores correlacionados à recompra). O PRD de dados diz que derivam das três áreas, mas não define cada um.~~ | Decidida na 10: taxa de recompra, retenção e satisfação no `GLOSSARY.md` (seção Diretoria), os fatores de recompra e o resumo por canal na spec (#96), e a forma da camada no ADR 0011. |
| ~~Painel de segurança: de onde vêm os resultados (execução ao vivo ou último resultado dos testes) e quem pode acessá-lo.~~ | Decidida na 11: da última execução de aceite, um comando próprio rodado no terminal contra o ambiente no ar, que grava o resultado num arquivo lido pela API (spec #104). Os quatro perfis o acessam, só com o interruptor de demonstração ligado (`PAINEL_DE_SEGURANCA`), que o compose liga. |
