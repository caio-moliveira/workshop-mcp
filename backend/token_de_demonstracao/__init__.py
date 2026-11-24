"""Tokens reais do provedor de identidade para os usuários de demonstração.

O percurso do fluxo de código com PKCE (`fluxo_de_codigo`) e o cadastro de usuários e aplicações
(`cadastro`). É uma ferramenta de desenvolvimento e de demonstração: roda na máquina local, com
as dependências do grupo `dev`, e não entra nas imagens dos serviços.
"""

from token_de_demonstracao.cadastro import (
    APLICACAO_WEB,
    USUARIOS_DE_DEMONSTRACAO,
    UsuarioDeDemonstracao,
    VariavelAusente,
    aplicacoes,
)
from token_de_demonstracao.fluxo_de_codigo import (
    Aplicacao,
    LoginRecusado,
    TelaDeLoginInesperada,
    tokens_pelo_fluxo_de_codigo,
)

__all__ = [
    "APLICACAO_WEB",
    "USUARIOS_DE_DEMONSTRACAO",
    "Aplicacao",
    "LoginRecusado",
    "TelaDeLoginInesperada",
    "UsuarioDeDemonstracao",
    "VariavelAusente",
    "aplicacoes",
    "tokens_pelo_fluxo_de_codigo",
]
