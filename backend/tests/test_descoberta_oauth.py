"""Descoberta OAuth no servidor MCP: a recusa aponta os metadados de recurso protegido (RFC 9728),
e eles apontam o realm do provedor (preparação da V1).

É o caminho que o MCP Inspector e os assistentes externos seguem para saber onde fazer login. O
servidor é criado pela fábrica, dentro do processo, confiando numa chave local. O mesmo caminho
contra o ambiente, com o login do Inspector, está em test_login_pelo_inspector.py.
"""

import pytest
from apoio import variavel
from chaves_locais import ChavesLocais, assinar, conteudo_valido, nova_chave
from cliente_mcp import (
    CAMINHO,
    CAMINHO_DOS_METADADOS,
    ORIGEM_DO_INSPECTOR,
    apontamento_dos_metadados,
    assert_recusado,
    pedir_ao_protocolo,
)
from provedor import DESTINATARIO_DO_MCP, emissor
from starlette.testclient import TestClient

CHAVE = nova_chave()


@pytest.fixture
def http(criar_mcp):
    with TestClient(criar_mcp(chaves=ChavesLocais(CHAVE))) as cliente:
        yield cliente


def test_sem_token_o_401_aponta_os_metadados(http):
    resposta = pedir_ao_protocolo(http, None, "tools/list")

    assert_recusado(resposta)
    assert resposta.headers["www-authenticate"] == f"Bearer {apontamento_dos_metadados()}"
    assert resposta.content == b""


def test_token_recusado_tambem_aponta_os_metadados(http):
    forjado = assinar(conteudo_valido(aud=DESTINATARIO_DO_MCP), nova_chave())

    resposta = pedir_ao_protocolo(http, forjado, "tools/list")

    assert_recusado(resposta)
    assert resposta.headers["www-authenticate"].startswith('Bearer error="invalid_token"')
    assert resposta.headers["www-authenticate"].endswith(apontamento_dos_metadados())


def test_os_metadados_respondem_sem_token_e_apontam_o_realm(http):
    resposta = http.get(CAMINHO_DOS_METADADOS)

    assert resposta.status_code == 200
    metadados = resposta.json()
    assert metadados["resource"] == variavel("ENDERECO_PUBLICO_DO_MCP") + CAMINHO
    assert metadados["authorization_servers"] == [emissor()]


@pytest.mark.parametrize("origem", [ORIGEM_DO_INSPECTOR, "http://outro.exemplo"])
def test_o_servidor_nao_libera_cors_para_navegador_nenhum(http, origem):
    """O Inspector fala com o servidor MCP e com o provedor pelo backend dele, não pelo
    navegador: o servidor não libera origem nenhuma, nem nos metadados, nem em `/mcp`."""
    previa = {"Origin": origem, "Access-Control-Request-Method": "POST"}

    metadados = http.get(CAMINHO_DOS_METADADOS, headers={"Origin": origem})
    consulta_previa = http.options(CAMINHO, headers=previa)
    recusa = http.post(CAMINHO, json={}, headers={"Origin": origem})

    assert metadados.status_code == 200
    for resposta in (metadados, consulta_previa, recusa):
        assert "access-control-allow-origin" not in resposta.headers
