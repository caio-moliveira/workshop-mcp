"""Auxiliares dos pedidos à API: pedir uma rota e reconhecer a forma única de cada recusa."""

RESPOSTA_DE_RECUSA = {"erro": "Não autenticado."}
# A mesma negação em toda rota de dados, para todo perfil sem acesso (RF-11).
RESPOSTA_DE_NEGACAO = {"erro": "Acesso negado."}
RESPOSTA_DE_PARAMETRO_INVALIDO = {"erro": "Parâmetro inválido."}
RESPOSTA_DE_INDISPONIVEL = {"erro": "Serviço indisponível."}

# As rotas que servem o painel de Vendas. Toda rota nova de Vendas entra aqui.
ROTAS_DE_VENDAS = ["/vendas/indicadores", "/vendas/evolucao", "/vendas/pedidos-recentes"]


def assert_recusado(resposta) -> None:
    """Toda recusa é idêntica: não diz qual verificação falhou (RS-08)."""
    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"
    assert resposta.json() == RESPOSTA_DE_RECUSA


def assert_negado(resposta) -> None:
    """A negação não diz se os dados existem nem qual verificação negou (RF-11)."""
    assert resposta.status_code == 403
    assert resposta.json() == RESPOSTA_DE_NEGACAO


def pedir(api, caminho: str, token: str | None = None, **parametros):
    """GET numa rota da API, com o token no cabeçalho Authorization e os parâmetros na URL."""
    cabecalhos = {"Authorization": f"Bearer {token}"} if token else {}
    return api.get(caminho, headers=cabecalhos, params=parametros)


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
