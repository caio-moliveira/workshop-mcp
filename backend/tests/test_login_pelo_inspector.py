"""O login pelo MCP Inspector contra o ambiente: o cliente `pulso-inspector` do realm, a descoberta
OAuth do serviço `mcp` do compose e um token real desse cliente.

É o caminho que o apresentador mostra no Inspector e que os assistentes externos usarão na V1: o
401 aponta os metadados de recurso protegido, eles apontam o realm, e o login no realm emite um
token que vale no servidor MCP e não na API. O registro dinâmico de clientes segue desligado: o
Inspector entra com o ID de um cliente pré-registrado.
"""

import httpx
import jwt
import pytest
from apoio import variavel
from cliente_mcp import (
    CAMINHO,
    CAMINHO_DOS_METADADOS,
    MCP_DO_AMBIENTE,
    ORIGEM_DO_INSPECTOR,
    apontamento_dos_metadados,
    assert_recusado,
    listar_ferramentas,
    pedir_ao_protocolo,
)
from provedor import (
    DESTINATARIO_DO_MCP,
    USUARIOS_DE_DEMONSTRACAO,
    administracao,
    emissor,
    tokens_pelo_fluxo_de_codigo,
)
from recusa import assert_recusado as assert_recusado_pela_api
from recusa import pedir_eu

from acesso import Perfil
from servidor_mcp.ferramentas import FERRAMENTAS

CLIENTE_DO_INSPECTOR = "pulso-inspector"
RETORNO_DO_INSPECTOR = f"{ORIGEM_DO_INSPECTOR}/oauth/callback"
OUTRA_ORIGEM = "http://localhost:5173"


def login_pelo_inspector(perfil: Perfil = Perfil.VENDAS) -> dict[str, str]:
    """Os tokens do login de um usuário de demonstração pelo cliente do Inspector, com PKCE."""
    usuario = next(u for u in USUARIOS_DE_DEMONSTRACAO if u.perfil == perfil)
    return tokens_pelo_fluxo_de_codigo(
        usuario.nome_de_usuario,
        usuario.senha(),
        aplicacao=CLIENTE_DO_INSPECTOR,
        retorno=RETORNO_DO_INSPECTOR,
    )


def _conteudo(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False})


@pytest.fixture
def mcp_do_ambiente():
    """Um cliente HTTP cru apontado para o servidor MCP do compose."""
    with httpx.Client(base_url=MCP_DO_AMBIENTE, timeout=10) as http:
        yield http


# --- Descoberta: do 401 ao realm ---


def test_sem_token_o_401_aponta_os_metadados(mcp_do_ambiente):
    resposta = pedir_ao_protocolo(mcp_do_ambiente, None, "tools/list")

    assert_recusado(resposta)
    assert resposta.headers["www-authenticate"] == f"Bearer {apontamento_dos_metadados()}"


def test_os_metadados_respondem_sem_token_e_apontam_o_realm(mcp_do_ambiente):
    resposta = mcp_do_ambiente.get(CAMINHO_DOS_METADADOS)

    assert resposta.status_code == 200
    metadados = resposta.json()
    assert metadados["resource"] == variavel("ENDERECO_PUBLICO_DO_MCP") + CAMINHO
    assert metadados["authorization_servers"] == [emissor()]
    # O servidor de autorização anunciado é mesmo o realm: quem o consulta chega ao emissor dos
    # tokens, ao login e ao endpoint de token.
    realm = httpx.get(f"{emissor()}/.well-known/openid-configuration", timeout=10).json()
    assert realm["issuer"] == emissor()


# --- Token real do cliente do Inspector ---


def test_token_do_inspector_traz_o_perfil_e_so_o_destinatario_do_mcp():
    conteudo = _conteudo(login_pelo_inspector()["access_token"])

    assert conteudo["perfil"] == "vendas"
    assert conteudo["azp"] == CLIENTE_DO_INSPECTOR
    destinatarios = conteudo["aud"] if isinstance(conteudo["aud"], list) else [conteudo["aud"]]
    assert destinatarios == [DESTINATARIO_DO_MCP]


def test_token_do_inspector_e_aceito_pelo_servidor_mcp():
    token = login_pelo_inspector()["access_token"]

    assert sorted(f.name for f in listar_ferramentas(MCP_DO_AMBIENTE, token)) == sorted(FERRAMENTAS)


def test_token_do_inspector_de_outro_perfil_recebe_a_lista_vazia():
    token = login_pelo_inspector(Perfil.PRODUTOS)["access_token"]

    assert listar_ferramentas(MCP_DO_AMBIENTE, token) == []


def test_token_do_inspector_e_recusado_pela_api(api):
    """O token do Inspector não traz `pulso-api` entre os destinatários (RS-02)."""
    assert_recusado_pela_api(pedir_eu(api, login_pelo_inspector()["access_token"]))


# --- O cliente no realm ---


def test_o_realm_declara_o_cliente_do_inspector_publico_com_pkce():
    with administracao() as realm:
        clientes = realm.get("/clients", params={"clientId": CLIENTE_DO_INSPECTOR}).json()

    assert len(clientes) == 1
    cliente = clientes[0]
    assert cliente["enabled"] is True
    assert cliente["publicClient"] is True
    assert cliente["standardFlowEnabled"] is True
    assert not cliente["implicitFlowEnabled"]
    assert not cliente["directAccessGrantsEnabled"]
    assert not cliente["serviceAccountsEnabled"]
    assert cliente["attributes"]["pkce.code.challenge.method"] == "S256"
    assert cliente["redirectUris"] == [RETORNO_DO_INSPECTOR]
    assert cliente["webOrigins"] == [ORIGEM_DO_INSPECTOR]


def test_o_login_do_inspector_nao_volta_para_outro_endereco():
    """O retorno é só o do Inspector: o provedor não manda o código para outro lugar."""
    usuario = next(u for u in USUARIOS_DE_DEMONSTRACAO if u.perfil == Perfil.VENDAS)

    with pytest.raises(httpx.HTTPStatusError):
        tokens_pelo_fluxo_de_codigo(
            usuario.nome_de_usuario,
            usuario.senha(),
            aplicacao=CLIENTE_DO_INSPECTOR,
            retorno=f"{OUTRA_ORIGEM}/oauth/callback",
        )


@pytest.mark.parametrize(
    ("origem", "liberada"), [(ORIGEM_DO_INSPECTOR, True), (OUTRA_ORIGEM, False)]
)
def test_o_provedor_libera_ao_navegador_so_a_origem_do_inspector(origem, liberada):
    """O endpoint de token responde ao navegador da origem do Inspector, e de nenhuma outra."""
    renovacao = httpx.post(
        f"{emissor()}/protocol/openid-connect/token",
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENTE_DO_INSPECTOR,
            "refresh_token": login_pelo_inspector()["refresh_token"],
        },
        headers={"Origin": origem},
        timeout=10,
    )

    liberou = renovacao.headers.get("access-control-allow-origin") == origem
    assert liberou is liberada
    if liberada:
        assert renovacao.status_code == 200


def test_o_registro_dinamico_de_clientes_continua_desligado():
    """Sem cliente pré-registrado não há login: um pedido anônimo de registro é recusado."""
    with administracao() as realm:
        antes = {c["clientId"] for c in realm.get("/clients").json()}

    pedido = httpx.post(
        f"{emissor()}/clients-registrations/openid-connect",
        json={"client_name": "registrado sem convite", "redirect_uris": [RETORNO_DO_INSPECTOR]},
        timeout=10,
    )

    assert pedido.status_code in (401, 403)
    with administracao() as realm:
        assert {c["clientId"] for c in realm.get("/clients").json()} == antes
