"""Auxiliares dos testes da API: pedir `GET /eu` e reconhecer a forma única de uma recusa."""

RESPOSTA_DE_RECUSA = {"erro": "Não autenticado."}


def assert_recusado(resposta) -> None:
    """Toda recusa é idêntica: não diz qual verificação falhou (RS-08)."""
    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"
    assert resposta.json() == RESPOSTA_DE_RECUSA


def pedir_eu(cliente, token: str):
    """GET /eu com o token no cabeçalho Authorization."""
    return cliente.get("/eu", headers={"Authorization": f"Bearer {token}"})
