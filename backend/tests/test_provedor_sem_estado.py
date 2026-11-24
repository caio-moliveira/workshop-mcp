"""O provedor de identidade não guarda estado: cada subida parte do realm versionado (ADR 0004)."""

import os
import time

import httpx
import pytest
from apoio import compose
from cliente_mcp import MCP_DO_AMBIENTE, pedir_ao_protocolo
from provedor import administracao, senha_de, token_pelo_fluxo_de_codigo

API_DO_AMBIENTE = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"

# Depois do reinício o provedor assina com chaves novas. A API e o servidor MCP do ambiente só
# buscam as chaves de novo diante de um identificador de chave desconhecido, e no máximo uma vez
# a cada 30 segundos desde a última busca (o cooldown do PyJWKClient, que protege contra quem
# força buscas com identificadores inventados). A espera cobre esse intervalo com folga.
LIMITE_DA_ESPERA_EM_SEGUNDOS = 90
INTERVALO_ENTRE_TENTATIVAS_EM_SEGUNDOS = 1


def _usuarios_chamados(nome_de_usuario: str) -> list:
    with administracao() as admin:
        resposta = admin.get("/users", params={"username": nome_de_usuario, "exact": "true"})
    resposta.raise_for_status()
    return resposta.json()


def _esperar_que_a_api_e_o_mcp_aceitem_um_token_novo() -> None:
    """Espera até a API e o servidor MCP do ambiente aceitarem um token assinado depois do
    reinício, para que os testes seguintes não recebam 401 por causa das chaves antigas."""
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))
    prazo = time.monotonic() + LIMITE_DA_ESPERA_EM_SEGUNDOS
    with (
        httpx.Client(base_url=API_DO_AMBIENTE, timeout=10) as api,
        httpx.Client(base_url=MCP_DO_AMBIENTE, timeout=10) as mcp,
    ):
        while True:
            api_aceita = api.get("/eu", headers={"Authorization": f"Bearer {token}"})
            mcp_aceita = pedir_ao_protocolo(mcp, token, "tools/list")
            if api_aceita.status_code == 200 and mcp_aceita.status_code == 200:
                return
            if time.monotonic() > prazo:
                pytest.fail(
                    f"depois de {LIMITE_DA_ESPERA_EM_SEGUNDOS} s, a API respondeu"
                    f" {api_aceita.status_code} e o servidor MCP {mcp_aceita.status_code}"
                    " a um token novo"
                )
            time.sleep(INTERVALO_ENTRE_TENTATIVAS_EM_SEGUNDOS)


def test_reiniciar_o_provedor_descarta_o_que_nao_esta_no_realm_versionado():
    with administracao() as admin:
        resposta = admin.post(
            "/users", json={"username": "resto.de.outra.execucao", "enabled": True}
        )
    assert resposta.status_code == 201, resposta.text

    reinicio = compose("restart", "keycloak")
    assert reinicio.returncode == 0, reinicio.stderr
    espera = compose("up", "-d", "--wait", "keycloak")
    assert espera.returncode == 0, espera.stderr

    assert _usuarios_chamados("resto.de.outra.execucao") == []
    assert len(_usuarios_chamados("ana.vendas")) == 1

    _esperar_que_a_api_e_o_mcp_aceitem_um_token_novo()
