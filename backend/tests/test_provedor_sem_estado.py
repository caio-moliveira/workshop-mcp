"""O provedor de identidade não guarda estado: cada subida parte do realm versionado (ADR 0004)."""

from apoio import compose
from provedor import administracao


def _usuarios_chamados(nome_de_usuario: str) -> list:
    with administracao() as admin:
        resposta = admin.get("/users", params={"username": nome_de_usuario, "exact": "true"})
    resposta.raise_for_status()
    return resposta.json()


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
