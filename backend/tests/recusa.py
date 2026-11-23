"""Auxiliar dos testes: a forma única de uma recusa da API."""

RESPOSTA_DE_RECUSA = {"erro": "Não autenticado."}


def assert_recusado(resposta) -> None:
    """Toda recusa é idêntica: não diz qual verificação falhou (RS-08)."""
    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"
    assert resposta.json() == RESPOSTA_DE_RECUSA
