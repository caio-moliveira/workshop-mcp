"""Auxiliares dos pedidos à API: pedir `GET /eu` e reconhecer a forma única de uma recusa."""

RESPOSTA_DE_RECUSA = {"erro": "Não autenticado."}


def assert_recusado(resposta) -> None:
    """Toda recusa é idêntica: não diz qual verificação falhou (RS-08)."""
    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"
    assert resposta.json() == RESPOSTA_DE_RECUSA


def pedir_eu(api, token: str | None = None, origem: str | None = None):
    """GET /eu com o token no cabeçalho Authorization e, se dada, a origem do navegador.

    `api` é qualquer cliente HTTP com `.get`: o da API no processo ou um `httpx.Client` apontado
    para a API do ambiente.
    """
    cabecalhos = {}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    if origem:
        cabecalhos["Origin"] = origem
    return api.get("/eu", headers=cabecalhos)
