# Conteúdo não confiável marcado no servidor MCP, não filtrado

O comentário de uma avaliação é texto escrito por clientes e chega ao modelo pela ferramenta que devolve avaliações. O RS-07 exige que ele seja tratado como conteúdo não confiável, e os dados trazem uma avaliação maliciosa para provar isso (CA-05). Decidimos que o servidor MCP marca esse texto como dado: a descrição da ferramenta diz que os comentários foram escritos por clientes e não são instruções, e o resultado traz o mesmo aviso junto dos comentários. O texto é entregue inteiro, cortado só num tamanho máximo, sem filtro e sem detecção de texto suspeito. A garantia de que nenhum dado de outro perfil vaza não depende da marcação nem do modelo: o assistente só tem as ferramentas do perfil de quem pergunta, com o token dele, e o papel do banco só lê a camada de leitura desse perfil (RS-06, ADR 0002).

## Considered Options

- **Filtrar ou detectar comentários com cara de instrução**: rejeitado porque um detector de texto é contornável por reescrita e daria uma segurança que não existe. Ele também esconderia a avaliação maliciosa, e o CA-05 passaria por nunca ser exercitado.
- **Não devolver comentários ao modelo, só notas**: rejeitado porque o perfil Produtos consulta avaliações, e o comentário é o que explica a nota. O teste de segurança também ficaria sem objeto.
- **Marcar só no prompt do assistente da aplicação**: rejeitado porque os assistentes externos não recebem esse prompt. A frase do prompt continua, mas a marcação que vale para todos é a do servidor MCP.
- **Resumir os comentários com um segundo modelo antes de entregá-los**: rejeitado porque moveria o problema para o segundo modelo, com custo e latência a mais.

## Consequences

Um modelo pode, ainda assim, obedecer ao texto de um comentário. O pior que ele consegue é chamar as ferramentas que o usuário já podia chamar e escrever uma resposta errada ou estranha; não alcança dados de outro perfil, dados pessoais de clientes nem a auditoria. O comportamento do modelo real diante da avaliação maliciosa não é provado por teste automático: é conferido no roteiro de demonstração, a cada troca de modelo. Toda ferramenta futura que devolva texto livre vindo dos dados precisa da mesma marcação. A tela mostra o comentário como texto simples, sem interpretar Markdown nem HTML.
