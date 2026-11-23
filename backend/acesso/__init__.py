"""O mecanismo de acesso compartilhado: valida o token e diz quem é o usuário e qual é seu perfil.

É o único lugar com essas regras. A API o usa; o servidor MCP vai usá-lo também.
"""

from acesso.validacao import (
    ChavesDoProvedor,
    ConfiguracaoDeAcesso,
    OrigemDeChaves,
    Perfil,
    TokenRecusado,
    UsuarioAutenticado,
    autenticar,
)

__all__ = [
    "ChavesDoProvedor",
    "ConfiguracaoDeAcesso",
    "OrigemDeChaves",
    "Perfil",
    "TokenRecusado",
    "UsuarioAutenticado",
    "autenticar",
]
