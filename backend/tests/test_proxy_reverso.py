"""O proxy reverso reúne o provedor de identidade e o servidor MCP sob um único endereço (V1).

É o endereço que o túnel publica. Os testes falam com ele pela porta local, sem túnel nem
internet, e comparam as respostas com as do serviço alcançado direto.
"""

import json
import re
import subprocess
from collections.abc import Iterator

import httpx
import pytest
from apoio import RAIZ_DO_PROJETO, compose
from cliente_mcp import (
    CAMINHO_DOS_METADADOS,
    MCP_DO_AMBIENTE,
    apontamento_dos_metadados,
    assert_recusado,
    pedir_ao_protocolo,
)
from provedor import (
    PROXY_DO_AMBIENTE,
    REALM,
    emissor,
    endereco_do_provedor,
    tela_de_login,
)


@pytest.fixture
def proxy() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=PROXY_DO_AMBIENTE, timeout=10) as cliente:
        yield cliente


def test_proxy_so_e_publicado_no_endereco_local():
    resultado = compose("port", "proxy", "80")

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip().startswith("127.0.0.1:")


def test_metadados_de_recurso_protegido_pelo_proxy_sao_os_do_servidor_mcp(proxy):
    direto = httpx.get(MCP_DO_AMBIENTE + CAMINHO_DOS_METADADOS, timeout=10)

    resposta = proxy.get(CAMINHO_DOS_METADADOS)

    assert resposta.status_code == 200
    assert resposta.json() == direto.json()


def test_recusa_do_protocolo_pelo_proxy_aponta_os_metadados(proxy):
    resposta = pedir_ao_protocolo(proxy, None, "tools/list")

    assert_recusado(resposta)
    assert resposta.headers["www-authenticate"] == f"Bearer {apontamento_dos_metadados()}"


METADADOS_DO_REALM = {
    "oauth-authorization-server": f"/realms/{REALM}/.well-known/oauth-authorization-server",
    "openid-configuration": f"/realms/{REALM}/.well-known/openid-configuration",
}


@pytest.mark.parametrize("formato", METADADOS_DO_REALM)
def test_metadados_do_realm_pelo_proxy_nos_caminhos_do_realm_e_da_raiz(proxy, formato):
    """Cada SDK tenta a descoberta numa ordem: o caminho do realm e o caminho da raiz com o realm
    inserido depois do `.well-known` (RFC 8414) dão os mesmos metadados.

    O emissor e a autorização são os do endereço público; os endpoints do canal interno (token,
    chaves...) seguem o endereço por onde o pedido chegou, aqui o do proxy.
    """
    direto = httpx.get(endereco_do_provedor() + METADADOS_DO_REALM[formato], timeout=10)

    pelo_realm = proxy.get(METADADOS_DO_REALM[formato])
    pela_raiz = proxy.get(f"/.well-known/{formato}/realms/{REALM}")

    for resposta in (pelo_realm, pela_raiz):
        assert resposta.status_code == 200
        metadados = resposta.json()
        assert metadados["issuer"] == emissor()
        assert metadados["token_endpoint"].startswith(PROXY_DO_AMBIENTE + "/")
        no_endereco_direto = resposta.text.replace(PROXY_DO_AMBIENTE, endereco_do_provedor())
        assert json.loads(no_endereco_direto) == direto.json()


def test_arquivos_do_tema_de_login_respondem_pelo_proxy(proxy):
    """A tela de login aponta os arquivos do tema em `/resources/...`, com uma versão que muda a
    cada subida do provedor: o teste os tira da própria tela."""
    arquivos = re.findall(r'(?:href|src)="(/resources/[^"]+/login/pulso/[^"]+)"', tela_de_login())
    assert arquivos, "a tela de login não aponta arquivo nenhum do tema"

    for arquivo in arquivos:
        assert proxy.get(arquivo).status_code == 200, arquivo


ENDERECO_DE_UM_TUNEL = "https://exemplo-de-tunel.trycloudflare.com"


@pytest.mark.parametrize("formato", METADADOS_DO_REALM)
def test_metadados_do_realm_atras_do_tunel_seguem_o_endereco_https_dele(proxy, formato):
    """O túnel entrega ao proxy o pedido com o host público e `X-Forwarded-Proto: https`. O
    provedor confia nesses cabeçalhos: o canal interno sai no endereço HTTPS do túnel, e o emissor
    continua o endereço público configurado, um só por vez."""
    resposta = proxy.get(
        f"/.well-known/{formato}/realms/{REALM}",
        headers={
            "Host": ENDERECO_DE_UM_TUNEL.removeprefix("https://"),
            "X-Forwarded-Proto": "https",
        },
    )

    assert resposta.status_code == 200
    metadados = resposta.json()
    assert metadados["issuer"] == emissor()
    assert metadados["token_endpoint"] == (
        f"{ENDERECO_DE_UM_TUNEL}/realms/{REALM}/protocol/openid-connect/token"
    )
    assert metadados["jwks_uri"].startswith(ENDERECO_DE_UM_TUNEL + "/")


def test_tunel_so_sobe_com_o_perfil_tunel():
    sem_perfil = compose("config", "--services")
    com_perfil = compose("--profile", "tunel", "config", "--services")

    assert sem_perfil.returncode == 0, sem_perfil.stderr
    assert com_perfil.returncode == 0, com_perfil.stderr
    assert "tunel" not in sem_perfil.stdout.split()
    assert "tunel" in com_perfil.stdout.split()
    assert "tunel-nomeado" not in com_perfil.stdout.split()


def test_tunel_nomeado_so_sobe_com_o_proprio_perfil():
    sem_perfil = compose("config", "--services")
    com_perfil = compose("--profile", "tunel-nomeado", "config", "--services")

    assert com_perfil.returncode == 0, com_perfil.stderr
    assert "tunel-nomeado" not in sem_perfil.stdout.split()
    assert "tunel-nomeado" in com_perfil.stdout.split()
    assert "tunel" not in com_perfil.stdout.split()


def test_tunel_nomeado_le_o_token_de_um_arquivo_e_aponta_para_o_proxy():
    """O token não passa pelo backend/.env: o contêiner do túnel não recebe as senhas do projeto."""
    config = compose("--profile", "tunel-nomeado", "config", "--format", "json")
    assert config.returncode == 0, config.stderr
    servicos = json.loads(config.stdout)["services"]
    tunel = servicos["tunel-nomeado"]

    assert "env_file" not in tunel
    assert "--token-file" in tunel["command"]
    assert "--token" not in tunel["command"]
    montagens = [v["target"] for v in tunel.get("volumes", [])]
    arquivo_do_token = tunel["command"][tunel["command"].index("--token-file") + 1]
    assert arquivo_do_token in montagens
    assert all(v.get("read_only") for v in tunel["volumes"])
    assert "proxy" in tunel["depends_on"]
    # Nenhum outro serviço monta o arquivo do token.
    for nome, servico in servicos.items():
        if nome != "tunel-nomeado":
            fontes = [v.get("source", "") for v in servico.get("volumes", [])]
            assert not any("token-do-tunel" in fonte for fonte in fontes), nome


def test_o_arquivo_do_token_do_tunel_fica_fora_do_git():
    resultado = subprocess.run(
        ["git", "check-ignore", "-q", "backend/token-do-tunel"],
        cwd=RAIZ_DO_PROJETO,
        check=False,
    )
    assert resultado.returncode == 0


@pytest.mark.parametrize(
    "caminho",
    [
        "/admin/",
        f"/admin/realms/{REALM}/users",
        "/realms/master/.well-known/openid-configuration",
        "/qualquer/coisa",
        "/",
    ],
)
def test_console_de_administracao_e_outros_caminhos_nao_existem_pelo_proxy(proxy, caminho):
    assert proxy.get(caminho).status_code == 404
