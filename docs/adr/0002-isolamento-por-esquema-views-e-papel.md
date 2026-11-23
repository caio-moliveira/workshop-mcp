# Isolamento por esquema, views e um papel por perfil

A garantia final de que um perfil não lê dados de outro precisa estar no banco, para valer mesmo com erro no código (RS-04). Decidimos que os dados de origem ficam em um esquema próprio, que cada perfil tem um esquema com views comuns formando sua camada de leitura, e que o papel de cada perfil recebe permissão de uso e leitura apenas no próprio esquema, sem nenhuma permissão nos dados de origem. As views leem os dados de origem com o direito do dono.

## Considered Options

- **Filtro por linha (RLS) sobre tabelas compartilhadas**: rejeitado porque a regra do projeto é por conjunto de dados, não por linha (o PRD exclui filtro por linha dentro de um perfil), e porque uma política mal escrita falha em silêncio, enquanto a falta de permissão em um esquema é recusada com erro.
- **Views materializadas ou tabelas copiadas por perfil**: rejeitadas por ora porque exigem um passo de atualização após a recarga e o volume do projeto não precisa delas. Continuam como opção para os indicadores da Diretoria.

## Consequences

Uma view nunca pode ser criada com o direito de quem consulta, senão o papel do perfil precisaria de acesso aos dados de origem. Colunas com dados pessoais são excluídas na definição da view, não por permissão de coluna.
