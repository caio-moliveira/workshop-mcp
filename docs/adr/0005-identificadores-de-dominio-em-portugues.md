# Identificadores de domínio em português também fora do banco

O ADR 0003 fixou o português só para o banco. Decidimos estender o mesmo princípio a todo identificador que nomeia um conceito do domínio: realm e clientes do provedor de identidade, claims do token, rotas da API, módulos e pacotes. Exemplos: claim `perfil`, rota `GET /eu`. Termos do próprio protocolo (`iss`, `aud`, `exp`, `Bearer`) e nomes de bibliotecas ficam como são. O motivo é o mesmo do ADR 0003: o token, a API e os testes falam a língua do glossário, sem tradução onde os termos possam divergir.
