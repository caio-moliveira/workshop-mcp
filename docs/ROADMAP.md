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
| V1 | Verificação com túnel: Claude e ChatGPT | 4a | Concluída (Claude verificado; ChatGPT pendente para a 7) |
| 4b | Auditoria e limite de frequência | 4a | Concluída |
| 5a | Chat de Vendas no painel lateral | 4b | Concluída |
| 5b | Chat expandido, rastreio e histórico | 5a | Concluída |
| 8 | Perfil Produtos | 5b | Livre |
| 9 | Perfil Comercial | 8 | Livre |
| 10 | Perfil Diretoria | 9 | Livre |
| 6 | Ambiente público | 4a | Bloqueada: nuvem e domínio |
| 7 | Claude e ChatGPT no ambiente público | 6, V1 | Bloqueada pela 6 |
| 11 | Painel de demonstração e aceite final | 7, 10 | Bloqueada pela 7 |

As entregas 6 e 7 mantêm seus números, mas ficam para depois: a decisão de nuvem e domínio foi adiada. As entregas 8 a 10 não dependem delas e seguem enquanto isso. A verificação V1 antecipa o maior risco da 7 sem depender da nuvem.

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
- **Cobre:** RF-27 e RF-28 (verificação antecipada; o fechamento é na entrega 7).
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
- **Resultado (25/11/2026):** concluída, no roteiro `docs/demonstracao/entrega-5b.md`, executado pela API com o modelo real. As conversas ficam no banco `historico`, que só a API alcança, com um papel próprio, e que a recarga não toca (ADR 0009); a conversa entregue ao modelo vem do banco, não do navegador. A pergunta sugerida foi respondida em cerca de 9 s, com `vendas_atrasos` por rota e por lojista, e os números citados conferem com o painel (9,0%, 1.411 atrasos em 15.622 entregues, nos 12 meses); a continuação pedindo uma tabela trouxe as 10 rotas com mais atraso, com taxas e participações consistentes; uma pergunta do segundo usuário de Vendas e outra de 90 dias também conferiram com o painel. A conversa lida de volta trouxe a situação, o identificador da pergunta e o rastreio (ferramenta, desfecho e duração). Entre `ana.vendas`, `vitor.vendas`, `bruno.produtos` e `diego.diretoria`, listar, ler, continuar e apagar a conversa de outro deu sempre o mesmo 404 de uma conversa inexistente (RF-18). O identificador da pergunta mostrado no rastreio apareceu, em `docker compose logs`, na linha da pergunta na API, nas das chamadas no servidor MCP e nas das consultas, sem o texto da pergunta (RNF-06). Apagar uma conversa não mudou a contagem da auditoria, e a recarga manteve as 212 conversas e os 244 itens do histórico. Lacunas: (1) a parte visual (modo expandido, lista de conversas, bloco de rastreio aberto e fechado, tabela rolando no painel lateral, teclado e Esc, tela pequena e os dois usuários de Vendas no navegador) não foi conferida; está no roteiro como conferência manual. (2) O ambiente da execução não foi subido com `docker compose down -v`: o histórico tinha as conversas deixadas pela suíte de testes, e a lista da Ana estava no teto de 50. (3) O modelo recebe do histórico só os textos de pergunta e resposta, sem as chamadas; numa continuação, ele "corrigiu" uma afirmação verdadeira, dizendo que não tinha consultado uma ferramenta que a auditoria mostra que ele consultou. (4) O modelo padrão errou por pouco uma conta que fez sobre os dados (ticket médio de R$ 1.054,01 em vez de R$ 1.053,87); os números copiados das ferramentas estavam certos. (5) Diferenças do modo expandido anotadas na implementação: a coluna de leitura é fixa em 820 px e fica abaixo de 760 px entre cerca de 768 e 1.100 px de largura, por causa dos 280 px da lista; o botão "Conversas" fica escondido no modo expandido; a área expandida não cobre a barra lateral, e um link dela troca a página por baixo sem recolher o painel. (6) A chamada negada como "não concluída" no rastreio só foi vista nos testes, com o modelo roteirizado; com o modelo real, ela não foi provocada nesta execução.

### 6. Ambiente público

- **O que passa a funcionar:** aplicação, API, servidor MCP e provedor de identidade ficam acessíveis por endereços públicos próprios com HTTPS. O banco fica só na rede interna.
- **Como demonstrar:**
  - Login e painel de Vendas pelo endereço público.
  - O banco não responde de fora da rede interna.
- **Depende de:** 4a (tecnicamente); na prática entra quando a decisão de nuvem e domínio for tomada.
- **Cobre:** RS-10, RNF-02.
- **Bloqueada por:** provedor de nuvem e domínio.

### 7. Claude e ChatGPT no ambiente público

- **O que passa a funcionar:** o usuário conecta o servidor MCP público no Claude e no ChatGPT, faz login pelo fluxo do protocolo e obtém os mesmos dados da aplicação.
- **Como demonstrar:**
  - Roteiro com a mesma pergunta na aplicação, no Claude e no ChatGPT, com o mesmo resultado.
  - Um usuário de outro perfil conectado não vê as ferramentas que não são dele.
- **Depende de:** 6 e V1.
- **Cobre:** RF-06 (cliente externo), RF-27, RF-28, RF-29, CA-06.
- **Observação:** a V1 verificou só o Claude. A primeira verificação do ChatGPT (modo desenvolvedor, registro dinâmico) acontece aqui; os passos esperados estão no roteiro da V1.

### 8. Perfil Produtos

- **O que passa a funcionar:** o usuário de Produtos tem camada de leitura, painel, ferramentas e chat próprios.
- **Como demonstrar:**
  - A matriz de isolamento cruza dois perfis reais nos dois sentidos, em rotas, ferramentas e credenciais do banco.
  - A avaliação maliciosa presente nos dados não altera o comportamento do agente.
  - A pergunta sugerida de Produtos é respondida.
- **Depende de:** 5b.
- **Cobre:** RF-02, RF-05, RF-10, RF-20, RS-04 (Produtos), RS-07, CA-05, CA-01 e CA-02 (ampliados); FE §6 (Produtos).

### 9. Perfil Comercial

- **O que passa a funcionar:** o usuário Comercial consulta o funil de lojistas na tela, nas ferramentas e no chat.
- **Como demonstrar:**
  - Matriz de isolamento com três perfis.
  - A pergunta sugerida do Comercial é respondida.
- **Depende de:** 8.
- **Cobre:** RF-02, RF-10, RF-20, RS-04 (Comercial), CA-01 e CA-02 (ampliados); FE §6 (Comercial).

### 10. Perfil Diretoria

- **O que passa a funcionar:** a Diretoria consulta indicadores consolidados na tela e no chat, sem acesso a registros individuais dos outros perfis.
- **Como demonstrar:**
  - Matriz de isolamento completa, quatro perfis contra todas as rotas e ferramentas.
  - A credencial da Diretoria é recusada nas camadas dos outros perfis.
  - Nenhum registro individual nem dado pessoal aparece na camada da Diretoria.
  - A pergunta "Por que os clientes compram uma vez e não voltam?" é respondida a partir dos indicadores consolidados.
- **Depende de:** 9.
- **Cobre:** RF-02, RF-04, RF-05, RS-04 (completos), CA-01, CA-02 (completos); FE §6 (Diretoria).

### 11. Painel de demonstração e aceite final

- **O que passa a funcionar:** o apresentador vê a matriz de cenários de segurança, com permitidos e negados, e os oito critérios de aceite rodam em um roteiro único.
- **Como demonstrar:**
  - Painel com os resultados dos testes de isolamento.
  - Roteiro de CA-01 a CA-08 passando.
  - CA-06 repetido para os quatro perfis no Claude e no ChatGPT.
  - Revisão dos critérios de aceite visuais.
- **Depende de:** 7 e 10.
- **Cobre:** CA-01 a CA-08 (fechamento), RNF-05 (medição final); FE §9 (painel de segurança), §13.

## Verificação de cobertura

Todos os requisitos com identificador aparecem em alguma entrega.

| Requisitos | Entregas |
| --- | --- |
| RF-01 a RF-05 | 1, 3, 8, 9, 10 |
| RF-06 a RF-09 | 2, 4a, 7 |
| RF-10 a RF-13 | 3, 4a, 5a, 8, 9 |
| RF-14 a RF-18 | 5a, 5b |
| RF-19 a RF-26 | 4a, 8, 9 |
| RF-27 a RF-29 | V1, 7 |
| RF-30 a RF-32 | 4b |
| RS-01 a RS-03 | 2, 4a, 5a |
| RS-04 | 1, 8, 9, 10 |
| RS-05, RS-06, RS-08 | 3, 4a, 5a |
| RS-07 | 8 |
| RS-09 | 1 |
| RS-10 | 6 |
| RS-11 | 4b |
| RNF-01, RNF-04, RNF-07 | 1 |
| RNF-02 | 6 |
| RNF-03 | 2 |
| RNF-05 | 3, 11 |
| RNF-06 | 5b |
| CA-01, CA-02 | 3, 4a, 8, 9, 10, 11 |
| CA-03 | 4a |
| CA-04 | 5a |
| CA-05 | 8 |
| CA-06 | 7, 11 |
| CA-07 | 4b |
| CA-08 | 1 |
| FE §1 a §13 | 2, 3, 5a, 5b, 8, 9, 10, 11 |
| PD inteiro | 1 |

Fica de fora:

- **FE §14** (prompt de implementação com dados fictícios): contraria o fatiamento de ponta a ponta. O restante do PRD de frontend é aplicado em cada entrega.

## Decisões em aberto

Questões listadas em `docs/PRD.md`:

| Decisão | Bloqueia |
| --- | --- |
| ~~Provedor de modelo padrão do chat~~ | Decidida na 5a: Anthropic, com `anthropic:claude-haiku-5-5` por padrão, trocável por `MODELO_DO_ASSISTENTE` sem mudança de código. |
| Provedor de nuvem e domínio | 6 e, por consequência, 7 e 11. Adiada. |
| ~~Como o agente obtém um token aceito pelo MCP: dois destinatários ou troca de token~~ | Decidida na 4a: dois destinatários, sem troca de token (ADR 0006). Não bloqueia mais a 5a. |
| Meta de 3 segundos do RNF-05 | Nenhuma. É medida na 3 e confirmada na 11. |
| ~~Limite de chamadas por usuário do RS-11~~ | Decidida na 4b: 30 chamadas por usuário por minuto, configurável (`LIMITE_DE_CHAMADAS_POR_USUARIO` e `JANELA_DO_LIMITE_EM_SEGUNDOS`). |

Lacunas que os PRDs não listam:

| Lacuna | Bloqueia |
| --- | --- |
| Definição dos indicadores da Diretoria (recompra, retenção, satisfação, fatores correlacionados à recompra). O PRD de dados diz que derivam das três áreas, mas não define cada um. | 10 |
| Painel de segurança: de onde vêm os resultados (execução ao vivo ou último resultado dos testes) e quem pode acessá-lo. | 11 |
