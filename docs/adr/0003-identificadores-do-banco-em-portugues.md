# Identificadores do banco em português

Os PRDs, o glossário e as perguntas dos usuários estão em português, e os nomes do banco chegam ao agente do chat por meio das ferramentas. Decidimos que tabelas, colunas e views usam os termos do glossário em português, sem acento, em minúsculas com sublinhado, em vez do inglês habitual em código. Assim o banco, os testes e o domínio falam a mesma língua, sem uma camada de tradução onde os termos possam divergir.

## Consequences

O código Python em volta do banco mistura palavras-chave e bibliotecas em inglês com nomes de domínio em português. Isso é aceito: o que não se aceita é traduzir um termo do glossário.
