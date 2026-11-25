"""A conferência, na auditoria, da chamada de ferramenta que o teste acabou de fazer."""

from apoio import ultima_chamada_de
from provedor import conteudo


def assert_auditada(token: str, ferramenta: str, argumentos: dict | None, resultado: str) -> None:
    """A última linha da auditoria do usuário do token é a chamada que o teste acabou de fazer.

    O usuário, o nome e o perfil vêm do token; os argumentos, inteiros, sem corte.
    """
    do_token = conteudo(token)
    linha = ultima_chamada_de(do_token["sub"])
    assert linha is not None
    assert linha["nome_do_usuario"] == do_token["name"]
    assert linha["perfil"] == do_token["perfil"]
    assert linha["ferramenta"] == ferramenta
    assert linha["parametros"] == (argumentos or {})
    assert linha["parametros_cortados"] is False
    assert linha["resultado"] == resultado
