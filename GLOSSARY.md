# Consulta de dados por perfil

Um marketplace brasileiro que conecta lojistas a clientes finais, cujos dados são consultados por quatro perfis, cada um restrito ao que lhe pertence. Este glossário fixa os termos usados em specs, tickets, testes e descrições de ferramentas.

## Language

### Acesso

**Usuário**:
Uma pessoa da empresa que consulta os dados pelo `pulso.`, pela aplicação ou por um cliente externo.
_Avoid_: Cliente (que é quem compra), conta, login

**Usuário de demonstração**:
Um dos quatro usuários fictícios, um por perfil, que existem para mostrar o isolamento entre perfis.
_Avoid_: Usuário de teste, mock

**Sessão**:
O período em que um usuário fica logado sem precisar entrar de novo. Termina por inatividade, pelo limite de duração ou quando ele sai.
_Avoid_: Login (que é o ato de entrar), token

**Perfil**:
A função de negócio de um usuário: Vendas, Produtos, Comercial ou Diretoria. Cada usuário tem exatamente um.
_Avoid_: Papel (é outra coisa), área, grupo, role

**Papel**:
A identidade no banco de dados que tem permissão de leitura em uma única camada de leitura. Cada perfil tem exatamente um papel.
_Avoid_: Perfil, usuário do banco

**Credencial**:
O par de usuário e senha com que um serviço se conecta ao banco usando um papel.
_Avoid_: Papel, login, conta

**Camada de leitura**:
O conjunto de dados preparado para um perfil, contendo apenas o que ele pode consultar. É a única coisa que telas e ferramentas leem.
_Avoid_: Visão, data mart, camada de consumo

**Dados de origem**:
Os dados brutos da empresa, que nenhum perfil lê diretamente.
_Avoid_: Origem (sozinho), tabelas de origem, base bruta

### Geração dos dados

**Data de referência**:
O último dia coberto pelos dados. Nada acontece depois dela, e ela não depende do dia em que os dados são gerados.
_Avoid_: Data atual, hoje, data de corte

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

**Recompra**:
O fato de um cliente fazer um segundo pedido com pagamento aprovado.
_Avoid_: Retorno, fidelização, retenção (que é um indicador da Diretoria)

### Produtos

**Avaliação**:
A nota de 1 a 5, com ou sem comentário, que um cliente dá a um produto de um pedido que recebeu. Há no máximo uma por pedido.
_Avoid_: Review, feedback, comentário (que é só o texto)

**Avaliação maliciosa**:
A única avaliação cujo comentário tenta dar instruções a um agente de IA. Existe para o teste de segurança.
_Avoid_: Avaliação envenenada, injeção, avaliação de teste

### Comercial

**Lead**:
Uma empresa em negociação para se tornar lojista.
_Avoid_: Prospecto, oportunidade, contato

**Canal**:
O meio pelo qual um lead chegou: Indicação, Orgânico, Mídia paga, Eventos ou Prospecção ativa.
_Avoid_: Origem, origem do lojista, fonte

**Etapa do funil**:
A posição de um lead na negociação: Novo, Contatado, Qualificado, Proposta, Fechado ou Perdido.
_Avoid_: Status do lead, fase, estágio
