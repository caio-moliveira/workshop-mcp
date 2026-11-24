"""O token de outra aplicação do mesmo provedor: real, válido, com perfil e recusado (CA-03).

O realm tem o cliente `pulso-outra-aplicacao`, que faz login como a aplicação mas não traz a API
nem o servidor MCP entre os destinatários. O token vem do fluxo de código com PKCE, e os pedidos
vão por HTTP ao serviço `mcp` do compose e à API.
"""

import httpx
import jwt
import pytest
import recusa
from cliente_mcp import MCP_DO_AMBIENTE, assert_recusado, pedir_ao_protocolo
from provedor import (
    APLICACAO,
    OUTRA_APLICACAO,
    aplicacao,
    emissor,
    senha_de,
    token_pelo_fluxo_de_codigo,
)
from recusa import ROTAS_DE_VENDAS, pedir, pedir_eu


def _conteudo(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False})


def _destinatarios(conteudo: dict) -> list[str]:
    """O `aud` como lista: o provedor o escreve como texto quando há um só."""
    destinatarios = conteudo.get("aud", [])
    return [destinatarios] if isinstance(destinatarios, str) else destinatarios


def _token_de_vendas_por(identificador: str) -> str:
    return token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"), identificador)


def test_o_token_da_outra_aplicacao_traz_o_perfil_e_so_ela_mesma_como_destinatario():
    conteudo = _conteudo(_token_de_vendas_por(OUTRA_APLICACAO))

    assert conteudo["azp"] == "pulso-outra-aplicacao"
    assert _destinatarios(conteudo) == ["pulso-outra-aplicacao"]
    assert conteudo["perfil"] == "vendas"
    assert conteudo["preferred_username"] == "ana.vendas"


def test_o_servidor_mcp_recusa_o_token_da_outra_aplicacao_e_aceita_o_da_aplicacao():
    """O mesmo usuário, o mesmo pedido: só muda a aplicação que pediu o token (CA-03)."""
    da_outra_aplicacao = _token_de_vendas_por(OUTRA_APLICACAO)
    da_aplicacao = _token_de_vendas_por(APLICACAO)

    with httpx.Client(base_url=MCP_DO_AMBIENTE, timeout=10) as mcp:
        recusada = pedir_ao_protocolo(mcp, da_outra_aplicacao, "tools/list")
        aceita = pedir_ao_protocolo(mcp, da_aplicacao, "tools/list")

    assert_recusado(recusada)
    assert "result" not in recusada.json()
    assert aceita.status_code == 200
    assert "vendas_indicadores" in [f["name"] for f in aceita.json()["result"]["tools"]]


@pytest.mark.parametrize("rota", ["/eu", *ROTAS_DE_VENDAS])
def test_a_api_recusa_o_token_da_outra_aplicacao(api, rota):
    token = _token_de_vendas_por(OUTRA_APLICACAO)

    recusa.assert_recusado(pedir(api, rota, token))


def test_a_api_aceita_o_mesmo_usuario_pelo_token_da_aplicacao(api):
    resposta = pedir_eu(api, _token_de_vendas_por(APLICACAO))

    assert resposta.status_code == 200
    assert resposta.json()["perfil"] == "vendas"


def test_a_outra_aplicacao_nao_abre_a_tela_de_login_sem_pkce():
    """Sem o desafio do PKCE o provedor devolve o erro ao retorno, sem pedir credenciais."""
    outra = aplicacao(OUTRA_APLICACAO)

    resposta = httpx.get(
        f"{emissor()}/protocol/openid-connect/auth",
        params={
            "client_id": outra.identificador,
            "response_type": "code",
            "scope": "openid",
            "redirect_uri": outra.retorno,
        },
        timeout=10,
    )

    assert resposta.status_code == 302
    assert resposta.headers["location"].startswith(f"{outra.retorno}?error=invalid_request")


def test_a_outra_aplicacao_nao_aceita_senha_direto():
    """Como a aplicação, só o fluxo de código: o cliente é público e não troca senha por token."""
    resposta = httpx.post(
        f"{emissor()}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": OUTRA_APLICACAO,
            "username": "ana.vendas",
            "password": senha_de("ana.vendas"),
        },
        timeout=10,
    )

    assert resposta.status_code == 400
    assert resposta.json()["error"] == "unauthorized_client"
