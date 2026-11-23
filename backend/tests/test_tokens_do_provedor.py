"""O que o provedor real põe em cada token do login da aplicação."""

import httpx
import jwt
from provedor import DESTINATARIO_DA_API, emissor, senha_de, tokens_pelo_fluxo_de_codigo


def _conteudo(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False})


def test_perfil_vai_so_no_token_de_acesso():
    """Quem decide o perfil é a API, pelo token de acesso: o navegador não o lê de outro lugar."""
    tokens = tokens_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))
    informacoes = httpx.get(
        f"{emissor()}/protocol/openid-connect/userinfo",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=10,
    )
    informacoes.raise_for_status()

    acesso = _conteudo(tokens["access_token"])
    assert acesso["perfil"] == "vendas"
    assert DESTINATARIO_DA_API in acesso["aud"]
    assert "perfil" not in _conteudo(tokens["id_token"])
    assert "perfil" not in informacoes.json()
