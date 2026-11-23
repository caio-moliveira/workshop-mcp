# Login na tela do provedor de identidade e frontend como cliente público

O PRD de frontend desenha uma tela de login própria, e o caminho mais curto seria um formulário em React que envia usuário e senha ao Keycloak. Decidimos que o login acontece sempre na tela do Keycloak, com um tema próprio versionado que segue o layout do FE §9, pelo fluxo de código de autorização com PKCE. O frontend é um cliente público que guarda o token só em memória e o envia à API como `Bearer`. Assim a senha nunca passa pela aplicação, e a API valida tokens do mesmo jeito que o servidor MCP fará com o Claude e o ChatGPT, que só sabem usar esse fluxo.

## Considered Options

- **Formulário em React com envio direto da senha (password grant)**: rejeitado porque o fluxo foi descontinuado no OAuth 2.1, expõe a senha à aplicação e criaria um segundo fluxo de login, diferente do usado pelos clientes MCP.
- **Backend for frontend, com a API guardando os tokens e o navegador só com um cookie de sessão**: rejeitado por ora porque traz cookie, proteção contra CSRF e sessão no servidor, e afasta a API do papel de simples validadora de token que ela divide com o servidor MCP.

## Consequences

A aparência da tela de login é mantida como tema do Keycloak, não como componente React. Recarregar a página apaga o token em memória; o retorno é silencioso enquanto a sessão no provedor estiver ativa.
