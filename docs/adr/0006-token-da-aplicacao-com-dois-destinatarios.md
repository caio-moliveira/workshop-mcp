# Token da aplicação com dois destinatários, API e servidor MCP

O servidor MCP aceita só tokens cujo destinatário inclui `pulso-mcp` (RS-01, RS-02), e o agente do chat precisa chamá-lo com a identidade do usuário logado, nunca com uma conta de serviço (RF-15). Decidimos que o cliente `pulso-web` emite tokens com os dois destinatários, `pulso-api` e `pulso-mcp`, e que o agente repassa ao servidor MCP o mesmo token que a aplicação já envia à API. A API e o servidor MCP são dois serviços da mesma aplicação, então um token emitido para ela valer nos dois não contraria o RS-02. Tokens emitidos para outros clientes continuam sem `pulso-mcp` e são recusados.

## Considered Options

- **Troca de token (RFC 8693) no Keycloak**: a API, como cliente confidencial, trocaria o token do usuário por outro só com `pulso-mcp`. Foi rejeitada por ora porque traz um segredo de cliente, um cliente confidencial e uma chamada a mais ao provedor por conversa, sem ganho de isolamento entre perfis: o perfil e o usuário seriam os mesmos nos dois tokens.

## Consequences

Um token vazado da aplicação vale também no servidor MCP até vencer (5 minutos). Se surgir um consumidor da API fora da aplicação, ele precisa de um cliente próprio, sem `pulso-mcp`.
