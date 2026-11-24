# Auditoria em banco próprio, fora da recarga

A auditoria (RF-30, RF-31) precisa sobreviver à recarga, que derruba e recria o banco `marketplace` (ADR 0001), e não pode ser lida por nenhuma ferramenta (RF-32). Decidimos que ela vive num banco próprio, `auditoria`, na mesma instância do Postgres. A carga cria só o que ainda não existe (o banco, o papel e a tabela) e nunca os derruba. O papel `auditoria`, usado pelo servidor MCP, tem apenas `insert` na tabela, sem `select`, `update` ou `delete`. Se a gravação falhar, a chamada é recusada: nenhuma chamada é respondida sem ficar registrada.

## Considered Options

- **Esquema dentro de `marketplace`**: rejeitado porque a recarga apaga o banco inteiro.
- **Serviço Postgres separado**: rejeitado porque deixa o ambiente mais pesado sem ganho de isolamento: bancos distintos já separam conexões e permissões.
- **Arquivo de registros no contêiner do MCP**: rejeitado porque é difícil de consultar nos testes e no painel da entrega 11, e não tem controle de permissão.
- **O servidor MCP criar o banco ao subir**: rejeitado porque exigiria a credencial do dono no servidor.
- **Responder mesmo quando a gravação falha**: rejeitado porque quebraria o CA-07 em silêncio.

## Consequences

O Postgres não tem volume: `docker compose down` apaga a auditoria junto com o resto, e é só assim que uma mudança na estrutura da tabela de auditoria chega a um ambiente já criado. Se o banco de auditoria cair, o servidor MCP para de responder às chamadas. O usuário fica na auditoria pelo `sub` do token; por isso os usuários de demonstração têm identificador fixo no realm, e o mesmo usuário não aparece com identificadores diferentes a cada subida do Keycloak.
