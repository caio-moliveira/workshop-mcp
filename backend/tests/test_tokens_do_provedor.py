"""O que o provedor real põe em cada token do login da aplicação."""

import httpx
import jwt
from provedor import (
    DESTINATARIO_DA_API,
    DESTINATARIO_DO_MCP,
    administracao,
    emissor,
    senha_de,
    tokens_pelo_fluxo_de_codigo,
)


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


def test_token_da_aplicacao_traz_os_dois_destinatarios():
    """ADR 0006: o mesmo token vale na API e no servidor MCP, e em mais nenhum serviço."""
    tokens = tokens_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))

    assert sorted(_conteudo(tokens["access_token"])["aud"]) == sorted(
        [DESTINATARIO_DA_API, DESTINATARIO_DO_MCP]
    )


def test_o_realm_declara_o_servidor_mcp_como_destinatario_que_nao_emite_tokens():
    with administracao() as realm:
        clientes = realm.get("/clients", params={"clientId": DESTINATARIO_DO_MCP}).json()

    assert len(clientes) == 1
    assert clientes[0]["enabled"] is True
    assert clientes[0]["publicClient"] is False
    fluxos = (
        "standardFlowEnabled",
        "implicitFlowEnabled",
        "directAccessGrantsEnabled",
        "serviceAccountsEnabled",
    )
    assert not any(clientes[0][fluxo] for fluxo in fluxos)
