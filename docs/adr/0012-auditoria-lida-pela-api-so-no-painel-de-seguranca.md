# Auditoria lida pela API só no painel de segurança, com um papel só de leitura

O painel de segurança mostra a última execução de aceite, que é uma foto tirada pelo comando. Na demonstração, o apresentador quer mostrar, enquanto usa o Claude, o ChatGPT ou o assistente do pulso., cada chamada ao servidor MCP aparecendo, permitida ou negada. Essas chamadas estão na auditoria, que nenhum serviço lia (ADR 0008). Decidimos que a API lê as últimas chamadas da auditoria, só com o interruptor de demonstração ligado (`PAINEL_DE_SEGURANCA=ligado`). Para isso, ela usa um papel próprio, `leitura_da_auditoria`, que só tem `select` na tabela e só se conecta ao banco da auditoria. A rota `GET /seguranca/chamadas` devolve as 20 mais recentes, com horário, nome do usuário, perfil, ferramenta e desfecho. Ela não devolve o `sub` nem os parâmetros, porque um parâmetro pode trazer texto qualquer de quem chamou. Desligado o interruptor, a rota não existe e a API não abre conexão com a auditoria.

## Considered Options

- **Dar `select` ao papel `auditoria`**: rejeitado porque o servidor MCP passaria a poder ler o que grava, e o RF-32 ficaria dependendo só de nenhuma ferramenta pedir isso.
- **A API ler com o papel dono**: rejeitado porque poria a credencial que cria e derruba bancos num serviço exposto ao navegador.
- **O servidor MCP guardar as últimas chamadas em memória e publicá-las numa rota**: rejeitado porque abriria no servidor MCP uma rota que não é do protocolo, e o que se mostraria não seria a auditoria de verdade.
- **Mostrar os parâmetros**: rejeitado porque eles são texto de quem chamou, e o painel é visto por qualquer perfil.
- **Empurrar as chamadas ao navegador (eventos do servidor)**: rejeitado por ora. Buscar a cada 3 segundos basta para a demonstração e reaproveita a fonte de dados das telas.

## Consequences

O RF-32 continua valendo: nenhuma ferramenta do MCP alcança a auditoria, o papel `auditoria` só insere, e os papéis de perfil não se conectam ao banco dela. O que muda é que a API passa a ler a auditoria quando o interruptor está ligado, e qualquer usuário logado vê as chamadas de todos os usuários, com os nomes das ferramentas de todos os perfis. É a mesma ressalva do painel de segurança, e só vale numa demonstração. Quem já tem o ambiente no ar precisa acrescentar `SENHA_DO_PAPEL_LEITURA_DA_AUDITORIA` ao `backend/.env`, refazer a carga e recriar a API. Sem a variável, a carga falha, e a API com o interruptor ligado não sobe.
