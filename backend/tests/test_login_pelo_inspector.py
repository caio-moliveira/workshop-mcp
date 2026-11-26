"""O login pelo MCP Inspector contra o ambiente: o cliente `pulso-inspector` do realm, a descoberta
OAuth do serviço `mcp` do compose e um token real desse cliente.

É o caminho que o apresentador mostra no Inspector e que os assistentes externos usarão na V1: o
401 aponta os metadados de recurso protegido, eles apontam o realm, e o login no realm emite um
token que vale no servidor MCP e não na API. O Inspector entra com o ID de um cliente
pré-registrado; o registro dinâmico, que os assistentes externos usam, está em
test_registro_dinamico.py.
"""

import httpx
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
    INSPECTOR,
    administracao,
    aplicacao,
    conteudo,
    destinatarios,
    emissor,
    endereco_do_provedor,
    tokens_pelo_fluxo_de_codigo,
    usuario_de,
)
from recusa import assert_recusado as assert_recusado_pela_api
from recusa import pedir_eu
from registros import ferramentas_de

from acesso import Perfil
from token_de_demonstracao import Aplicacao, fluxo_de_codigo

CLIENTE_DO_INSPECTOR = INSPECTOR
RETORNO_DO_INSPECTOR = f"{ORIGEM_DO_INSPECTOR}/oauth/callback"
OUTRA_ORIGEM = "http://localhost:5173"


def login_pelo_inspector(perfil: Perfil = Perfil.VENDAS) -> dict[str, str]:
    """Os tokens do login de um usuário de demonstração pelo cliente do Inspector, com PKCE."""
    usuario = usuario_de(perfil)
    return tokens_pelo_fluxo_de_codigo(
        usuario.nome_de_usuario, usuario.senha(), CLIENTE_DO_INSPECTOR
    )


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


@pytest.mark.parametrize(
    "caminho",
    [
        # RFC 8414 com o caminho do emissor depois do .well-known: o que o SDK do Inspector lê.
        "/.well-known/oauth-authorization-server/realms/pulso",
        "/realms/pulso/.well-known/oauth-authorization-server",
        "/realms/pulso/.well-known/openid-configuration",
    ],
)
def test_os_metadados_do_realm_nao_anunciam_acesso_offline(caminho):
    """O SDK do Inspector pede `offline_access` quando os metadados do realm o anunciam e a opção
    de pedir o token de renovação está ligada (o padrão). Os usuários não têm acesso offline, e o
    login pararia na troca do código; sem o anúncio, o pedido sai só com `openid`."""
    metadados = httpx.get(f"{endereco_do_provedor()}{caminho}", timeout=10)

    assert metadados.status_code == 200
    assert metadados.json()["issuer"] == emissor()
    assert "offline_access" not in metadados.json().get("scopes_supported", [])


# --- Token real do cliente do Inspector ---


def test_token_do_inspector_traz_o_perfil_e_so_o_destinatario_do_mcp():
    do_token = conteudo(login_pelo_inspector()["access_token"])

    assert do_token["perfil"] == "vendas"
    assert do_token["azp"] == CLIENTE_DO_INSPECTOR
    assert destinatarios(do_token) == [DESTINATARIO_DO_MCP]


def test_o_inspector_pede_os_escopos_anunciados_e_recebe_o_mesmo_token():
    """O SDK do Inspector pede os escopos dos metadados de recurso protegido (`openid pulso-mcp`).
    O provedor recusaria um escopo que o cliente não tem; o `pulso-inspector` o aceita e o token
    continua com o perfil e só o destinatário do MCP."""
    usuario = usuario_de(Perfil.VENDAS)
    with httpx.Client(base_url=MCP_DO_AMBIENTE, timeout=10) as mcp:
        escopos = " ".join(mcp.get(CAMINHO_DOS_METADADOS).json()["scopes_supported"])
    inspector = Aplicacao(CLIENTE_DO_INSPECTOR, RETORNO_DO_INSPECTOR, escopos)

    token = fluxo_de_codigo.tokens_pelo_fluxo_de_codigo(
        emissor(), inspector, usuario.nome_de_usuario, usuario.senha()
    )["access_token"]

    do_token = conteudo(token)
    assert do_token["perfil"] == "vendas"
    assert destinatarios(do_token) == [DESTINATARIO_DO_MCP]
    assert sorted(f.name for f in listar_ferramentas(MCP_DO_AMBIENTE, token)) == ferramentas_de(
        Perfil.VENDAS
    )


def test_token_do_inspector_e_aceito_pelo_servidor_mcp():
    token = login_pelo_inspector()["access_token"]

    assert sorted(f.name for f in listar_ferramentas(MCP_DO_AMBIENTE, token)) == ferramentas_de(
        Perfil.VENDAS
    )


def test_token_do_inspector_de_outro_perfil_recebe_a_lista_vazia():
    token = login_pelo_inspector(Perfil.DIRETORIA)["access_token"]

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
    usuario = usuario_de(Perfil.VENDAS)

    with pytest.raises(httpx.HTTPStatusError):
        fluxo_de_codigo.tokens_pelo_fluxo_de_codigo(
            emissor(),
            Aplicacao(CLIENTE_DO_INSPECTOR, f"{OUTRA_ORIGEM}/oauth/callback"),
            usuario.nome_de_usuario,
            usuario.senha(),
        )


@pytest.mark.parametrize(
    ("origem", "liberada"), [(ORIGEM_DO_INSPECTOR, True), (OUTRA_ORIGEM, False)]
)
def test_o_provedor_libera_ao_navegador_so_a_origem_do_inspector(origem, liberada):
    """O endpoint de token responde ao navegador da origem do Inspector, e de nenhuma outra.

    O pedido é a troca do código, o primeiro que o navegador do Inspector faria ao endpoint de
    token. Não é a renovação: o provedor recusa a renovação de um token cujo `iat` é anterior ao
    início da sessão, e isso acontece quando o relógio dele salta entre o login e a emissão.
    """
    usuario = usuario_de(Perfil.VENDAS)
    pedido = fluxo_de_codigo.troca_do_codigo(
        emissor(), aplicacao(CLIENTE_DO_INSPECTOR), usuario.nome_de_usuario, usuario.senha()
    )

    troca = httpx.post(
        f"{emissor()}/protocol/openid-connect/token",
        data=pedido,
        headers={"Origin": origem},
        timeout=10,
    )

    liberou = troca.headers.get("access-control-allow-origin") == origem
    assert liberou is liberada
    if liberada:
        assert troca.status_code == 200
        assert "access_token" in troca.json()
