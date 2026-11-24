"""O registro dinâmico de um assistente externo e o token que ele obtém (RF-28, ADR 0007).

O assistente (o Claude ou o ChatGPT) se registra sozinho no realm, sem convite, com o endereço de
retorno dele, e leva o usuário ao login pedindo o escopo `pulso-mcp`, anunciado nos metadados de
recurso protegido. Os pedidos vão por HTTP, como os servidores do assistente fariam: o registro, o
login e o token pelo endereço local do proxy reverso, o mesmo que o túnel publica; as ferramentas ao
serviço `mcp` do compose e o `/eu` à API. O emissor esperado continua o endereço público. O código
de autorização é capturado do redirecionamento, sem segui-lo até o assistente.
"""

import httpx
import pytest
from cliente_mcp import (
    MCP_DO_AMBIENTE,
    assert_recusado,
    chamar,
    listar_ferramentas,
    pedir_ao_protocolo,
)
from provedor import (
    CAMINHO_DO_REGISTRO,
    DESTINATARIO_DO_MCP,
    administracao,
    conteudo,
    destinatarios,
    emissor,
    realm_pelo_proxy,
    usuario_de,
)
from recusa import assert_recusado as assert_recusado_pela_api
from recusa import pedir_eu

from acesso import Perfil
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
        realm_pelo_proxy() + CAMINHO_DO_REGISTRO,
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


def _token(assistente: Aplicacao, perfil: Perfil = Perfil.VENDAS) -> str:
    """O login do usuário de demonstração do perfil, pelo proxy, e o token do assistente."""
    usuario = usuario_de(perfil)
    return fluxo_de_codigo.tokens_pelo_fluxo_de_codigo(
        realm_pelo_proxy(), assistente, usuario.nome_de_usuario, usuario.senha()
    )["access_token"]


# --- O registro ---


def test_os_metadados_do_realm_anunciam_o_endpoint_de_registro():
    """Pelo proxy, o emissor é o público e o registro sai no endereço por onde o pedido chegou."""
    metadados = httpx.get(
        f"{realm_pelo_proxy()}/.well-known/oauth-authorization-server", timeout=10
    ).json()

    assert metadados["issuer"] == emissor()
    assert metadados["registration_endpoint"] == realm_pelo_proxy() + CAMINHO_DO_REGISTRO


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
    do_token = conteudo(_token(_assistente()))

    assert do_token["iss"] == emissor()
    assert destinatarios(do_token) == [DESTINATARIO_DO_MCP]
    assert do_token["perfil"] == "vendas"
    # O nome vem do escopo pulso-mcp: o cliente registrado com escopo, como o Claude faz, não
    # recebe o profile, e o servidor MCP exige o nome.
    assert do_token["name"] == usuario_de(Perfil.VENDAS).nome


@pytest.mark.parametrize("retorno", [RETORNO_DO_CLAUDE, RETORNO_DO_CHATGPT])
def test_vendas_lista_as_cinco_ferramentas_e_chama_uma(retorno):
    token = _token(_assistente(retorno))

    assert sorted(f.name for f in listar_ferramentas(MCP_DO_AMBIENTE, token)) == sorted(FERRAMENTAS)
    resultado = chamar(MCP_DO_AMBIENTE, token, "vendas_indicadores", {"periodo": "12m"})
    assert not resultado.is_error
    assert resultado.structured_content


def test_a_diretoria_recebe_a_lista_vazia():
    """Mesmo assistente, outro perfil: o servidor MCP só lista as ferramentas do perfil do token."""
    assert listar_ferramentas(MCP_DO_AMBIENTE, _token(_assistente(), Perfil.DIRETORIA)) == []


def test_a_api_recusa_o_token_do_assistente(api):
    assert_recusado_pela_api(pedir_eu(api, _token(_assistente())))


def test_sem_pedir_o_escopo_o_token_e_recusado_pelo_servidor_mcp():
    """O escopo `pulso-mcp` é opcional: quem não o pede recebe um token sem destinatário nem
    perfil, e o servidor MCP o recusa pelo mesmo caminho de sempre."""
    token = _token(_assistente(escopo="openid"))

    assert DESTINATARIO_DO_MCP not in destinatarios(conteudo(token))
    with httpx.Client(base_url=MCP_DO_AMBIENTE, timeout=10) as mcp:
        assert_recusado(pedir_ao_protocolo(mcp, token, "tools/list"))
