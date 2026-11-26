# Consulta de dados por perfil

Um marketplace brasileiro que conecta lojistas a clientes finais, cujos dados são consultados por quatro perfis, cada um restrito ao que lhe pertence. Este glossário fixa os termos usados em specs, tickets, testes e descrições de ferramentas.

## Language

### Acesso

**Usuário**:
Uma pessoa da empresa que consulta os dados pelo `pulso.`, pela aplicação ou por um assistente externo.
_Avoid_: Cliente (que é quem compra), conta, login

**Usuário de demonstração**:
Um dos usuários fictícios que existem para mostrar o isolamento. Cada perfil tem um; Vendas tem dois, para mostrar também o isolamento entre usuários do mesmo perfil.
_Avoid_: Usuário de teste, mock

**Sessão**:
O período em que um usuário fica logado sem precisar entrar de novo. Termina por inatividade, pelo limite de duração ou quando ele sai.
_Avoid_: Login (que é o ato de entrar), token

**Perfil**:
A função de negócio de um usuário: Vendas, Produtos, Comercial ou Diretoria. Cada usuário tem exatamente um.
_Avoid_: Papel (é outra coisa), área, grupo, role

**Papel**:
Uma identidade no banco de dados com permissão para uma única coisa. O papel de um perfil lê uma única camada de leitura, e cada perfil tem exatamente um papel. O papel da auditoria só grava na auditoria, não lê nada e não pertence a nenhum perfil.
_Avoid_: Perfil, usuário do banco

**Credencial**:
O par de usuário e senha com que um serviço se conecta ao banco usando um papel.
_Avoid_: Papel, login, conta

**Camada de leitura**:
O conjunto de dados preparado para um perfil, contendo apenas o que ele pode consultar. É a única coisa que telas e ferramentas leem.
_Avoid_: Visão, data mart, camada de consumo

**Ferramenta**:
Uma consulta oferecida pelo servidor MCP, que pertence a um único perfil e só aparece para ele.
_Avoid_: Tool (sozinho), endpoint, função

**Assistente**:
O assistente de IA da própria aplicação, com quem o usuário conversa em linguagem natural. Só consulta dados pelas ferramentas, com a identidade do usuário.
_Avoid_: Agente, chat (que é a tela), bot, IA (sozinho)

**Pergunta**:
O que o usuário escreve ao assistente.
_Avoid_: Mensagem, prompt, consulta

**Resposta**:
O que o assistente devolve a uma pergunta.
_Avoid_: Mensagem, saída, retorno

**Conversa**:
A sequência de perguntas e respostas de um usuário com o assistente.
_Avoid_: Histórico (que é o conjunto das conversas gravadas), sessão, thread

**Histórico**:
As conversas gravadas de um usuário, que só ele reabre. Um usuário pode ter várias.
_Avoid_: Conversa (que é uma só), auditoria (que é das chamadas), memória

**Rastreio**:
A lista das chamadas que produziram uma resposta, com a ferramenta, o desfecho e a duração de cada uma. O usuário a vê junto da resposta.
_Avoid_: Auditoria (que é o registro permanente de todas as chamadas), log, trace

**Assistente externo**:
Um assistente de IA de terceiros, como o Claude ou o ChatGPT, conectado ao servidor MCP com o login do usuário.
_Avoid_: Cliente externo, cliente MCP (Cliente é quem compra)

**Chamada**:
O pedido de um usuário para executar uma ferramenta, qualquer que seja o desfecho: permitida, negada, com parâmetro inválido, com falha ou barrada pelo limite de frequência. Listar as ferramentas não é chamada.
_Avoid_: Requisição, acesso, uso

**Auditoria**:
O registro permanente de todas as chamadas, com usuário, perfil, ferramenta, parâmetros, resultado e horário. Nenhuma ferramenta a lê, e a recarga não a apaga.
_Avoid_: Log (que é o diagnóstico do serviço), histórico (que é o da conversa), trilha

**Limite de frequência**:
O número máximo de chamadas que um usuário pode fazer numa janela de tempo. Quando ele passa do limite, só as chamadas dele são barradas.
_Avoid_: Rate limit, cota, throttling

**Dados de origem**:
Os dados brutos da empresa, que nenhum perfil lê diretamente.
_Avoid_: Origem (sozinho), tabelas de origem, base bruta

### Geração dos dados

**Data de referência**:
O último dia coberto pelos dados. Nada acontece depois dela, e ela não depende do dia em que os dados são gerados.
_Avoid_: Data atual, hoje, data de corte

**Período**:
A janela de dias, terminando na data de referência, sobre a qual um painel ou indicador é calculado: últimos 30 dias, 90 dias, 12 meses ou 24 meses.
_Avoid_: Intervalo, filtro de datas, janela

**Carga**:
O processo que cria o banco inteiro a partir do nada: estrutura, dados e permissões.
_Avoid_: Seed, ingestão, migração, importação

**Recarga**:
Uma nova carga pedida para devolver o banco ao estado inicial.
_Avoid_: Reset, limpeza, restauração

### Vendas

**Cliente**:
A pessoa que compra no marketplace.
_Avoid_: Consumidor, comprador, usuário

**Lojista**:
A empresa que vende no marketplace. Todo lojista nasceu de um lead fechado.
_Avoid_: Vendedor, seller, loja, parceiro

**Pedido**:
Uma compra de um cliente a um único lojista, com seus itens, um pagamento e uma entrega.
_Avoid_: Compra, venda, ordem

**Rota**:
O trajeto de um pedido, do estado do lojista ao estado do cliente.
_Avoid_: Trecho, percurso, frete (que é o valor cobrado)

**Atraso**:
A situação de um pedido entregue depois da data prometida.
_Avoid_: Prazo vencido (é outra coisa), demora

**Prazo vencido**:
A situação de um pedido ainda em trânsito cuja data prometida já passou na data de referência.
_Avoid_: Atraso, pendente

**Receita**:
A soma dos pagamentos aprovados dos pedidos de um período, com itens e frete.
_Avoid_: Faturamento, vendas (que é o perfil), GMV

**Taxa de atraso**:
A parte dos pedidos entregues que chegou com atraso. Pedidos com prazo vencido não entram.
_Avoid_: Índice de atraso, atrasos (sozinho)

**Taxa de aprovação**:
A parte dos pedidos cujo pagamento foi aprovado.
_Avoid_: Conversão (que é do Comercial)

**Recompra**:
O fato de um cliente fazer um segundo pedido com pagamento aprovado.
_Avoid_: Retorno, fidelização, retenção (que é um indicador da Diretoria)

### Produtos

**Produto**:
Um item que um lojista oferece no marketplace, com nome, preço e uma categoria.
_Avoid_: Item (que é a linha de um pedido), SKU, mercadoria

**Catálogo**:
O conjunto de todos os produtos do marketplace. Não depende do período.
_Avoid_: Produtos ativos, estoque, portfólio

**Avaliação**:
A nota de 1 a 5, com ou sem comentário, que um cliente dá a um produto de um pedido que recebeu. Há no máximo uma por pedido.
_Avoid_: Review, feedback, comentário (que é só o texto)

**Avaliação maliciosa**:
A única avaliação cujo comentário tenta dar instruções a um agente de IA. Existe para o teste de segurança.
_Avoid_: Avaliação envenenada, injeção, avaliação de teste

**Reclamação**:
Uma avaliação com nota 1 ou 2, com ou sem comentário.
_Avoid_: Avaliação negativa, crítica, queixa

**Taxa de reclamação**:
A parte das avaliações de um período que são reclamações.
_Avoid_: Índice de reclamação, reclamações (sozinho, que é a contagem)

**Produto mal avaliado**:
Um produto cuja nota média, nas avaliações de um período, fica abaixo de 3,0, desde que tenha recebido pelo menos 3 avaliações nesse período.
_Avoid_: Produto ruim, produto problemático, produto com reclamação

### Comercial

**Lead**:
Uma empresa que entrou no funil para se tornar lojista, esteja em negociação, fechada ou perdida.
_Avoid_: Prospecto, oportunidade, contato

**Canal**:
O meio pelo qual um lead chegou: Indicação, Orgânico, Mídia paga, Eventos ou Prospecção ativa.
_Avoid_: Origem, origem do lojista, fonte

**Etapa do funil**:
A posição de um lead na negociação: Novo, Contatado, Qualificado, Proposta, Fechado ou Perdido.
_Avoid_: Status do lead, fase, estágio

**Lead em negociação**:
Um lead que ainda não fechou nem foi perdido: está em Novo, Contatado, Qualificado ou Proposta.
_Avoid_: Lead aberto, lead ativo, oportunidade

**Lead perdido**:
Um lead na etapa Perdido, cuja negociação terminou sem ele virar lojista.
_Avoid_: Lead descartado, lead inativo, churn

**Novo lojista**:
Um lead que fechou, contado no dia do fechamento.
_Avoid_: Lead convertido, lojista ativo, cliente novo

**Conversão**:
O número de novos lojistas de um período dividido pelo número de leads criados no mesmo período, no total ou por canal. É uma razão entre dois movimentos do período, não a parte de um conjunto: um lead criado antes do período pode fechar dentro dele.
_Avoid_: Taxa de fechamento, taxa de aprovação (que é de Vendas), aproveitamento

### Diretoria

**Indicador consolidado**:
Um número calculado sobre um grupo de registros, por dia, semana, mês, canal ou outra dimensão fechada. É a única coisa que a Diretoria consulta: nunca um cliente, pedido, lead, avaliação, lojista ou produto individual.
_Avoid_: Indicador agregado, KPI, métrica

**Taxa de recompra**:
A parte dos clientes com pedido aprovado num período que fez uma recompra nesse período. Em períodos curtos ela é maior, porque quem compra de novo pesa mais entre os poucos clientes do período.
_Avoid_: Recompra (sozinho, que é o fato), fidelização, retenção

**Retenção**:
A parte dos clientes com pedido aprovado no período anterior, de mesmo tamanho, que teve outro pedido aprovado no período. Não existe quando não há período anterior nos dados.
_Avoid_: Taxa de recompra (que olha quem comprou agora, não quem comprou antes), churn, fidelização

**Satisfação**:
A nota média das avaliações de um período. É o mesmo número que Produtos vê como nota média.
_Avoid_: NPS, índice de satisfação, CSAT
