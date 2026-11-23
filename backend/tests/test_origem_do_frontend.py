"""CORS: só a origem do frontend pode chamar a API pelo navegador."""

from apoio import variavel
from provedor import senha_de, token_pelo_fluxo_de_codigo

ORIGEM_ESTRANHA = "http://site-estranho.example"


def consulta_previa(cliente, origem: str):
    """A consulta que o navegador faz antes de mandar o cabeçalho Authorization."""
    return cliente.options(
        "/eu",
        headers={
            "Origin": origem,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )


def pedir_eu_de(cliente, origem: str, token: str | None = None):
    cabecalhos = {"Origin": origem}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    return cliente.get("/eu", headers=cabecalhos)


def test_origem_do_frontend_passa_pela_consulta_previa(cliente_da_api):
    origem = variavel("ENDERECO_DO_FRONTEND")

    resposta = consulta_previa(cliente_da_api, origem)

    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == origem
    assert "authorization" in resposta.headers["access-control-allow-headers"].lower()


def test_origem_do_frontend_le_a_resposta_de_eu(cliente_da_api):
    origem = variavel("ENDERECO_DO_FRONTEND")
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))

    resposta = pedir_eu_de(cliente_da_api, origem, token)

    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == origem


def test_recusa_tambem_e_legivel_pela_origem_do_frontend(cliente_da_api):
    """Sem isso, o navegador esconde o 401 e o frontend não sabe que deve voltar ao login."""
    origem = variavel("ENDERECO_DO_FRONTEND")

    resposta = pedir_eu_de(cliente_da_api, origem)

    assert resposta.status_code == 401
    assert resposta.headers["access-control-allow-origin"] == origem


def test_outra_origem_nao_passa_pela_consulta_previa(cliente_da_api):
    resposta = consulta_previa(cliente_da_api, ORIGEM_ESTRANHA)

    assert "access-control-allow-origin" not in resposta.headers


def test_outra_origem_nao_le_a_resposta_de_eu(cliente_da_api):
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))

    resposta = pedir_eu_de(cliente_da_api, ORIGEM_ESTRANHA, token)

    assert "access-control-allow-origin" not in resposta.headers
