# Registro dinâmico com o escopo `pulso-mcp` opcional no realm

O RF-28 pede que o assistente externo se registre e inicie o login sozinho, pelo fluxo de autorização do protocolo MCP. No Keycloak, um cliente registrado dinamicamente não recebe os mapeadores que cada cliente fixo carrega (destinatário `pulso-mcp` e claim `perfil`), e sem eles o servidor MCP recusa o token. Decidimos ligar o registro dinâmico anônimo no realm, com a política de hosts confiáveis aceitando só endereços de retorno do Claude e do ChatGPT, e criar um escopo de cliente `pulso-mcp` com os dois mapeadores, marcado como escopo opcional padrão do realm. Os metadados de recurso protegido anunciam esse escopo, o assistente o pede e o token dele sai com `pulso-mcp` e sem `pulso-api`, a regra do ADR 0006 para clientes que falam com o servidor MCP. Os clientes fixos do realm declaram os próprios escopos e não recebem o novo, exceto o `pulso-inspector`: o Inspector pede os escopos anunciados nos metadados, e o provedor recusa o login de um cliente que pede um escopo que não tem. Para ele o escopo é opcional e não muda o token, que já traz o destinatário e o perfil pelos mapeadores do próprio cliente. O escopo também traz o nome do usuário: o Claude manda os escopos no registro, e o provedor então deixa o cliente sem o `profile`, de onde o nome viria.

## Considered Options

- **Um cliente fixo por assistente, com o Client ID digitado nas configurações avançadas do conector**: não exige registro dinâmico, mas não cumpre o "automático" do RF-28 e obriga a manter os endereços de retorno de cada assistente no realm.
- **Escopo `pulso-mcp` como escopo padrão (não opcional) do realm**: todo cliente novo receberia `pulso-mcp` sem pedir, inclusive os criados no futuro para outros fins, o que contraria o ADR 0006.

## Consequences

Enquanto o registro anônimo está ligado, qualquer um que alcance o provedor consegue registrar um cliente, mas só com endereço de retorno nos hosts confiáveis, e o token ainda depende do login de um usuário. Como o realm é reimportado a cada subida (ADR 0004), os clientes registrados somem num reinício e o conector do assistente precisa ser refeito.

Com o escopo novo declarado no arquivo do realm, o Keycloak deixa de criar sozinho os escopos embutidos (`profile`, `email`, `basic`, `roles` e os demais) e de ligá-los aos clientes que ele mesmo cria. O arquivo passa a declarar esses escopos e os escopos de cada cliente, inclusive do `admin-cli`, que os testes usam como "outro serviço". Os demais clientes embutidos (`account`, `account-console`, `broker`, `realm-management`, `security-admin-console`) ficam sem escopos; a aplicação não os usa.
