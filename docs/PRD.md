# PRD técnico: consulta de dados por perfil com servidor MCP

Nov 23, 2026 · @Caio

A aplicação permite que quatro perfis de uma empresa de e-commerce consultem dados por tela e por chat, cada um restrito ao que lhe pertence. O mesmo acesso é exposto por um servidor MCP, usado pelo chat da aplicação, pelo Claude e pelo ChatGPT. Os requisitos do frontend estão em `docs/PRD_frontend.md` e não são repetidos aqui.

## Objetivo e escopo

O objetivo é provar, em um projeto completo, que um agente de IA pode consultar dados de negócio sem vazar informação entre perfis.

Faz parte do escopo:

- Banco de dados com os dados da empresa já carregados e uma camada de leitura separada por perfil.
- API que serve as telas e hospeda o agente do chat.
- Servidor MCP com ferramentas somente leitura.
- Autenticação e perfis em um provedor de identidade.
- Conexão do servidor MCP ao Claude e ao ChatGPT.
- Auditoria e testes automatizados de isolamento entre perfis.

Fica fora do escopo:

- Pipeline de ingestão ou transformação de dados.
- Qualquer operação de escrita nos dados de negócio.
- Cadastro de usuários pela aplicação; eles são criados no provedor de identidade.
- Acesso de usuários externos à empresa.
- Filtro por linha dentro de um mesmo perfil.

## Perfis e regra de acesso

Cada usuário tem exatamente um perfil, e cada perfil lê apenas o próprio conjunto de dados, na tela e no chat.

| Perfil | Dados que consulta |
| --- | --- |
| Vendas | Pedidos, receita, pagamentos e entregas |
| Produtos | Catálogo, categorias e avaliações por produto |
| Comercial | Funil de lojistas: leads, origem e negócios fechados |
| Diretoria | Indicadores consolidados do negócio |

A Diretoria não tem acesso aos dados dos outros perfis. Ela consulta indicadores já consolidados, preparados na camada de leitura.

## Visão geral da solução

O usuário faz login uma vez. As telas consultam a API, e o chat consulta o servidor MCP por meio do agente. Nos dois caminhos, o perfil contido no token define o que pode ser lido.

| Componente | Responsabilidade |
| --- | --- |
| Banco de dados | Guarda os dados da empresa e expõe uma camada de leitura por perfil |
| Provedor de identidade | Autentica os usuários, atribui o perfil e emite os tokens |
| API | Serve os dados das telas e hospeda o agente do chat |
| Agente do chat | Interpreta a pergunta, chama as ferramentas do MCP e redige a resposta |
| Servidor MCP | Expõe as consultas como ferramentas, com controle de acesso por perfil |
| Frontend | Telas e chat, conforme `docs/PRD_frontend.md` |
| Clientes externos | Claude e ChatGPT, conectados ao mesmo servidor MCP |

## Requisitos funcionais

### Dados

- **RF-01** O banco deve conter os dados da empresa carregados por um processo repetível, que recria o estado inicial a qualquer momento.
- **RF-02** Deve existir uma camada de leitura separada por perfil, contendo apenas o que aquele perfil pode consultar.
- **RF-03** Telas e ferramentas do MCP devem ler somente dessa camada, nunca das tabelas de origem.
- **RF-04** A camada da Diretoria deve trazer indicadores já agregados, sem expor registros individuais dos outros perfis.
- **RF-05** A camada de leitura não deve conter dados pessoais de clientes além do necessário para os indicadores.

### Autenticação e perfis

- **RF-06** Todo acesso, por tela, chat ou cliente externo, deve exigir login no provedor de identidade.
- **RF-07** O perfil deve ser atribuído ao usuário no provedor de identidade e viajar dentro do token.
- **RF-08** O sistema deve ter quatro usuários de demonstração, um por perfil.
- **RF-09** A sessão deve expirar, e um token vencido deve ser recusado em qualquer ponto de entrada.

### API

- **RF-10** A API deve servir os dados de cada tela conforme o perfil do token recebido.
- **RF-11** Uma requisição a dados de outro perfil deve ser negada, sem indicar se o dado existe.
- **RF-12** A API deve oferecer um ponto de entrada para o chat, com a resposta transmitida em tempo real.
- **RF-13** A API e o servidor MCP devem usar o mesmo mecanismo de acesso a dados, para que a regra de perfil exista em um só lugar.

### Chat da aplicação

- **RF-14** O chat deve responder perguntas em linguagem natural usando apenas as ferramentas do servidor MCP.
- **RF-15** O agente deve chamar o MCP com a identidade do usuário logado, nunca com uma conta de serviço.
- **RF-16** O modelo de linguagem deve ser trocável por configuração, sem mudança de código.
- **RF-17** Quando a pergunta envolver dados de outro perfil, o chat deve informar que não tem acesso, sem inventar resposta.
- **RF-18** O histórico de conversa não deve ser compartilhado entre usuários nem entre perfis.

### Servidor MCP

- **RF-19** O servidor deve expor um conjunto pequeno de ferramentas somente leitura, orientadas a perguntas de negócio.
- **RF-20** Cada ferramenta deve pertencer a um único perfil.
- **RF-21** A lista de ferramentas devolvida ao cliente deve conter apenas as do perfil do usuário.
- **RF-22** Toda chamada deve verificar o perfil novamente, mesmo que a ferramenta não tenha sido listada.
- **RF-23** As ferramentas devem aceitar apenas parâmetros previstos e validados, como período e agrupamento. Não deve existir ferramenta de consulta livre.
- **RF-24** Cada ferramenta deve ter uma descrição clara do que responde, para o modelo escolher corretamente.
- **RF-25** As respostas devem ser estruturadas e limitadas em tamanho.
- **RF-26** O servidor deve funcionar sem guardar estado entre requisições.

### Clientes externos

- **RF-27** O mesmo servidor MCP deve aceitar conexões do Claude e do ChatGPT, sem versão separada para cada um.
- **RF-28** O cliente externo deve conseguir se registrar e iniciar o login do usuário de forma automática, seguindo o fluxo de autorização do protocolo MCP.
- **RF-29** O usuário conectado por um cliente externo deve ter exatamente o mesmo acesso que tem na aplicação.

### Auditoria

- **RF-30** Toda chamada de ferramenta deve ser registrada com usuário, perfil, ferramenta, parâmetros, resultado e horário.
- **RF-31** Tentativas negadas devem ser registradas da mesma forma.
- **RF-32** O registro de auditoria não deve ser acessível pelas ferramentas do MCP.

### Frontend

Os requisitos de telas, navegação e chat estão em `docs/PRD_frontend.md` e devem ser seguidos como estão escritos lá.

## Requisitos de segurança

Nenhum perfil pode obter dados de outro, por tela, por chat ou por cliente externo. A garantia final fica no banco: mesmo com um erro no código, a leitura indevida é recusada.

- **RS-01** O token deve ser validado em toda requisição: assinatura, emissor, destinatário e validade.
- **RS-02** Tokens emitidos para outro serviço devem ser recusados, mesmo que válidos.
- **RS-03** O perfil deve vir sempre do token, nunca de um parâmetro enviado pelo cliente ou pelo modelo.
- **RS-04** A conexão com o banco deve usar uma credencial própria de cada perfil, com permissão de leitura apenas na camada daquele perfil.
- **RS-05** O padrão deve ser negar: uma ferramenta ou rota sem perfil declarado não pode ser publicada.
- **RS-06** Nenhuma regra de acesso pode depender do frontend ou de instruções dadas ao modelo.
- **RS-07** Textos vindos dos dados, como avaliações de clientes, devem ser tratados como conteúdo não confiável e nunca como instrução.
- **RS-08** Mensagens de erro não devem revelar a estrutura do banco, nomes internos ou a existência de dados de outro perfil.
- **RS-09** Segredos e chaves devem ficar fora do repositório, em configuração de ambiente.
- **RS-10** Toda comunicação externa deve usar HTTPS.
- **RS-11** O servidor MCP deve limitar a frequência de chamadas por usuário.

## Requisitos não funcionais

- **RNF-01** O ambiente completo deve subir com um único comando, em contêineres.
- **RNF-02** Aplicação, API, servidor MCP e provedor de identidade devem ter endereços públicos próprios. O banco deve ficar apenas na rede interna.
- **RNF-03** A configuração do provedor de identidade deve ser versionada e importada automaticamente na subida.
- **RNF-04** As versões das dependências devem ser fixadas.
- **RNF-05** Consultas das telas e das ferramentas devem responder em até 3 segundos com o volume de dados do projeto.
- **RNF-06** Os logs devem permitir acompanhar uma pergunta do chat até as consultas feitas no banco.
- **RNF-07** Toda mudança deve passar pela integração contínua antes de entrar na branch principal.

## Stack e restrições

| Camada | Tecnologia |
| --- | --- |
| Banco de dados | Postgres |
| API | Python com FastAPI |
| Agente do chat | PydanticAI |
| Servidor MCP | FastMCP |
| Provedor de identidade | Keycloak |
| Frontend | React, conforme `docs/PRD_frontend.md` |
| Infraestrutura | Docker Compose, com proxy reverso e HTTPS |

Restrições:

- Não usar ferramenta de transformação de dados; a camada de leitura é definida no próprio banco.
- Não usar gateway de modelos; o provedor do modelo é escolhido por configuração.
- Não criar uma segunda implementação das regras de acesso fora do mecanismo compartilhado entre API e servidor MCP.

## Critérios de aceite

O projeto está pronto quando os oito critérios abaixo passam, os sete primeiros de forma automatizada ou roteirizada.

- **CA-01** Cada um dos quatro usuários vê na aplicação apenas os dados do próprio perfil.
- **CA-02** Um teste automatizado percorre todos os perfis contra todas as ferramentas e rotas, com sucesso apenas nas combinações permitidas.
- **CA-03** Um token emitido para outra aplicação é recusado pelo servidor MCP.
- **CA-04** Pedidos no chat para ignorar as regras ou mostrar dados de outro perfil não retornam esses dados.
- **CA-05** Um texto malicioso inserido nos dados não altera o comportamento do agente.
- **CA-06** O mesmo usuário obtém os mesmos dados na aplicação, no Claude e no ChatGPT.
- **CA-07** Toda chamada feita nos testes, permitida ou negada, aparece na auditoria.
- **CA-08** O ambiente sobe do zero com um comando, e os dados voltam ao estado inicial quando solicitado.

## Questões em aberto

Duas decisões ainda dependem de definição e podem mudar requisitos acima. Três já foram tomadas e ficam marcadas.

- [x] Qual provedor de modelo de linguagem o chat usa por padrão? Decidido na entrega 5a: Anthropic, com o modelo `anthropic:claude-haiku-5-5`, trocável pela variável `MODELO_DO_ASSISTENTE` sem mudança de código (RF-16). A chave fica em `ANTHROPIC_API_KEY`.
- [ ] Qual provedor de nuvem e qual domínio hospedam o ambiente público?
- [x] Como o agente do chat obtém um token aceito pelo servidor MCP: um token com dois destinatários ou uma troca de token? Decidido na entrega 4a: dois destinatários, sem troca de token (`docs/adr/0006-token-da-aplicacao-com-dois-destinatarios.md`).
- [ ] A meta de 3 segundos do RNF-05 é adequada? É um valor inicial, sem medição.
- [x] Qual é o limite de chamadas por usuário do RS-11? Decidido na entrega 4b: 30 chamadas por usuário por minuto, em janela deslizante, configurável pelas variáveis `LIMITE_DE_CHAMADAS_POR_USUARIO` e `JANELA_DO_LIMITE_EM_SEGUNDOS`.
