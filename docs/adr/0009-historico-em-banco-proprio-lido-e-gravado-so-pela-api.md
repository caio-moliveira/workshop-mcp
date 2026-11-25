# Histórico em banco próprio, lido e gravado só pela API

O histórico das conversas (RF-18) precisa ser isolado por usuário sem depender do navegador (RS-06) e precisa sobreviver à recarga, que derruba e recria o banco `marketplace` (ADR 0001). Decidimos que ele vive num banco próprio, `historico`, na mesma instância do Postgres, criado pela carga como o da auditoria (ADR 0008): só o que ainda não existe, nunca derrubado. Um papel próprio, usado só pela API, lê e grava nele. Cada conversa guarda o identificador e o perfil do usuário que a criou, lidos do token, e só é devolvida quando os dois batem com o token de quem pede.

## Considered Options

- **Guardar no navegador (`localStorage`)**: rejeitado porque o isolamento entre usuários dependeria do frontend e da máquina usada, e não seria testável pela API.
- **Esquema dentro de `auditoria`**: rejeitado porque o ADR 0008 garante que nenhum serviço lê aquele banco e que o papel dele só insere. O histórico precisa de leitura, e de exclusão quando o usuário apaga uma conversa.
- **Esquema dentro de `marketplace`**: rejeitado porque a recarga apaga o banco inteiro.
- **O navegador continuar reenviando a conversa, com o banco só como cópia**: rejeitado porque manteria aberta a conversa forjada pelo navegador. A API lê do banco a conversa que entrega ao modelo.

## Consequences

A API ganha a sua primeira credencial de escrita. Até aqui ela só lia, com o papel do perfil de quem pede. O papel do histórico não alcança o banco `marketplace` nem o `auditoria`, e o servidor MCP e os papéis de perfil não se conectam ao banco `historico`: nenhuma ferramenta lê o histórico. O texto das perguntas passa a ficar gravado em banco, e continua fora dos logs. Como o Postgres não tem volume, `docker compose down` apaga o histórico, e é só assim que uma mudança na estrutura das tabelas chega a um ambiente já criado. Um usuário que muda de perfil deixa de ver as conversas antigas. Apagar uma conversa não toca na auditoria.
