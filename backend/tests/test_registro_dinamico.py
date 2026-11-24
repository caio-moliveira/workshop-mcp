"""O registro dinâmico de um assistente externo e o token que ele obtém (RF-28, ADR 0007).

O assistente (o Claude ou o ChatGPT) se registra sozinho no realm, sem convite, com o endereço de
retorno dele, e leva o usuário ao login pedindo o escopo `pulso-mcp`, anunciado nos metadados de
recurso protegido. Os pedidos vão por HTTP ao provedor, ao serviço `mcp` do compose e à API, como
os servidores do assistente fariam; o código de autorização é capturado do redirecionamento, sem
segui-lo até o assistente.
"""

import httpx
import jwt
import pytest
from cliente_mcp import (
    MCP_DO_AMBIENTE,
    assert_recusado,
    chamar,
    listar_ferramentas,
    pedir_ao_protocolo,
)
from provedor import (
    DESTINATARIO_DO_MCP,
    administracao,
    emissor,
    senha_de,
)
from recusa import assert_recusado as assert_recusado_pela_api
from recusa import pedir_eu

from servidor_mcp.ferramentas import FERRAMENTAS
from token_de_demonstracao import Aplicacao, fluxo_de_codigo

RETORNO_DO_CLAUDE = "https://claude.ai/api/mcp/auth_callback"
RETORNO_DO_CHATGPT = "https://chatgpt.com/connector_platform_oauth_redirect"
ESCOPO_DO_MCP = "openid pulso-mcp"


def _registrar(retorno: str) -> httpx.Response:
    """Registra um cliente público, como o assistente faz ao adicionar o conector.

    O pedido leva os escopos anunciados nos metadados de recurso protegido, como o Claude manda:
    o `openid` também, que no provedor não é um escopo de cliente e a política de escopos do
    registro anônimo precisa aceitar.
    """
    return httpx.post(
        f"{emissor()}/clients-registrations/openid-connect",
        json={
            "client_name": "assistente externo",
            "redirect_uris": [retorno],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": ESCOPO_DO_MCP,
        },
        timeout=10,
    )


def _assistente(retorno: str = RETORNO_DO_CLAUDE, escopo: str = ESCOPO_DO_MCP) -> Aplicacao:
    """Um assistente recém-registrado, pronto para levar o usuário ao login."""
    registro = _registrar(retorno)
    registro.raise_for_status()
    return Aplicacao(registro.json()["client_id"], retorno, escopo)


def _token(assistente: Aplicacao, nome_de_usuario: str = "ana.vendas") -> str:
    return fluxo_de_codigo.tokens_pelo_fluxo_de_codigo(
        emissor(), assistente, nome_de_usuario, senha_de(nome_de_usuario)
    )["access_token"]


def _conteudo(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False})


def _destinatarios(conteudo: dict) -> list[str]:
    """O `aud` como lista: o provedor o escreve como texto quando há um só."""
    destinatarios = conteudo.get("aud", [])
    return [destinatarios] if isinstance(destinatarios, str) else destinatarios


# --- O registro ---


def test_os_metadados_do_realm_anunciam_o_endpoint_de_registro():
    metadados = httpx.get(f"{emissor()}/.well-known/oauth-authorization-server", timeout=10).json()

    assert metadados["registration_endpoint"] == (
        f"{emissor()}/clients-registrations/openid-connect"
    )


@pytest.mark.parametrize("retorno", [RETORNO_DO_CLAUDE, RETORNO_DO_CHATGPT])
def test_o_assistente_se_registra_com_o_proprio_retorno(retorno):
    registro = _registrar(retorno)

    assert registro.status_code == 201
    assert registro.json()["client_id"]
    assert registro.json()["redirect_uris"] == [retorno]


@pytest.mark.parametrize(
    "retorno",
    [
        "http://localhost:6274/oauth/callback",
        "https://atacante.exemplo/retorno",
        "https://claude.ai.atacante.exemplo/retorno",
    ],
)
def test_o_registro_com_retorno_fora_dos_hosts_confiaveis_e_recusado(retorno):
    """Ninguém registra um cliente que devolva o código de autorização para outro lugar."""
    with administracao() as realm:
        antes = {c["clientId"] for c in realm.get("/clients").json()}

    registro = _registrar(retorno)

    assert registro.status_code == 403
    with administracao() as realm:
        assert {c["clientId"] for c in realm.get("/clients").json()} == antes


# --- O token do assistente ---


def test_o_token_do_assistente_traz_o_perfil_e_so_o_destinatario_do_mcp():
    """Login e consentimento do usuário: o token traz o que o servidor MCP exige e não vale na API
    (ADR 0006)."""
    conteudo = _conteudo(_token(_assistente()))

    assert _destinatarios(conteudo) == [DESTINATARIO_DO_MCP]
    assert conteudo["perfil"] == "vendas"
    # O nome vem do escopo pulso-mcp: o cliente registrado com escopo, como o Claude faz, não
    # recebe o profile, e o servidor MCP exige o nome.
    assert conteudo["name"] == "Ana Ribeiro"


@pytest.mark.parametrize("retorno", [RETORNO_DO_CLAUDE, RETORNO_DO_CHATGPT])
def test_vendas_lista_as_cinco_ferramentas_e_chama_uma(retorno):
    token = _token(_assistente(retorno))

    assert sorted(f.name for f in listar_ferramentas(MCP_DO_AMBIENTE, token)) == sorted(FERRAMENTAS)
    resultado = chamar(MCP_DO_AMBIENTE, token, "vendas_indicadores", {"periodo": "12m"})
    assert not resultado.is_error
    assert resultado.structured_content


def test_a_diretoria_recebe_a_lista_vazia():
    """Mesmo assistente, outro perfil: o servidor MCP só lista as ferramentas do perfil do token."""
    assert listar_ferramentas(MCP_DO_AMBIENTE, _token(_assistente(), "diego.diretoria")) == []


def test_a_api_recusa_o_token_do_assistente(api):
    assert_recusado_pela_api(pedir_eu(api, _token(_assistente())))


def test_sem_pedir_o_escopo_o_token_e_recusado_pelo_servidor_mcp():
    """O escopo `pulso-mcp` é opcional: quem não o pede recebe um token sem destinatário nem
    perfil, e o servidor MCP o recusa pelo mesmo caminho de sempre."""
    token = _token(_assistente(escopo="openid"))

    assert DESTINATARIO_DO_MCP not in _destinatarios(_conteudo(token))
    with httpx.Client(base_url=MCP_DO_AMBIENTE, timeout=10) as mcp:
        assert_recusado(pedir_ao_protocolo(mcp, token, "tools/list"))
