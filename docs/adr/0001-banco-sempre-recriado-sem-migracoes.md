# Banco sempre recriado pela carga, sem ferramenta de migração

Os dados de negócio são sintéticos, somente leitura e gerados com semente fixa, então não existe estado a preservar entre versões da estrutura. Decidimos que a estrutura do banco fica em arquivos SQL aplicados em ordem pela carga, e que a recarga percorre exatamente o mesmo caminho da primeira subida: derruba tudo e recria. Não usamos Alembic nem ferramenta equivalente.

## Considered Options

- **Ferramenta de migração desde o início**: rejeitada porque versionaria mudanças de um estado que nunca é mantido, e criaria um segundo caminho ("migrar") ao lado de "recriar".
- **Recarga por truncar e reinserir**: rejeitada porque "subir do zero" e "voltar ao estado inicial" poderiam divergir sem que nenhum teste percebesse.

## Consequences

A auditoria (entrega 4b) e o histórico de conversa (entrega 5b) são dados que a recarga não deve apagar. Quando chegarem, esta decisão precisa ser reaberta: ou esses dados vivem fora do alcance da carga, ou passam a ter migrações próprias.

A auditoria foi resolvida no ADR 0008: banco próprio, que a carga cria só quando não existe e nunca derruba.
