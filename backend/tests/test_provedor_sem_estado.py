"""O provedor de identidade não guarda estado: cada subida parte do realm versionado (ADR 0004)."""

import httpx
from apoio import compose, variavel
from provedor import endereco_do_provedor


def _token_de_administrador() -> str:
    resposta = httpx.post(
        f"{endereco_do_provedor()}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": variavel("KC_BOOTSTRAP_ADMIN_USERNAME"),
            "password": variavel("KC_BOOTSTRAP_ADMIN_PASSWORD"),
        },
        timeout=10,
    )
    resposta.raise_for_status()
    return resposta.json()["access_token"]


def _usuarios_chamados(nome: str) -> list:
    resposta = httpx.get(
        f"{endereco_do_provedor()}/admin/realms/pulso/users",
        params={"username": nome, "exact": "true"},
        headers={"Authorization": f"Bearer {_token_de_administrador()}"},
        timeout=10,
    )
    resposta.raise_for_status()
    return resposta.json()


def test_reiniciar_o_provedor_descarta_o_que_nao_esta_no_realm_versionado():
    resposta = httpx.post(
        f"{endereco_do_provedor()}/admin/realms/pulso/users",
        json={"username": "resto.de.outra.execucao", "enabled": True},
        headers={"Authorization": f"Bearer {_token_de_administrador()}"},
        timeout=10,
    )
    assert resposta.status_code == 201, resposta.text

    reinicio = compose("restart", "keycloak")
    assert reinicio.returncode == 0, reinicio.stderr
    espera = compose("up", "-d", "--wait", "keycloak")
    assert espera.returncode == 0, espera.stderr

    assert _usuarios_chamados("resto.de.outra.execucao") == []
    assert len(_usuarios_chamados("ana.vendas")) == 1
