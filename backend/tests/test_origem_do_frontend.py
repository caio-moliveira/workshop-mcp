"""CORS: só a origem do frontend pode chamar a API pelo navegador."""

from apoio import variavel
from provedor import senha_de, token_pelo_fluxo_de_codigo
from recusa import pedir_eu

ORIGEM_ESTRANHA = "http://site-estranho.example"


def consulta_previa(api, origem: str):
    """A consulta que o navegador faz antes de mandar o cabeçalho Authorization."""
    return api.options(
        "/eu",
        headers={
            "Origin": origem,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )


def test_origem_do_frontend_passa_pela_consulta_previa(api):
    origem = variavel("ENDERECO_DO_FRONTEND")

    resposta = consulta_previa(api, origem)

    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == origem
    assert "authorization" in resposta.headers["access-control-allow-headers"].lower()


def test_origem_do_frontend_le_a_resposta_de_eu(api):
    origem = variavel("ENDERECO_DO_FRONTEND")
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))

    resposta = pedir_eu(api, token, origem=origem)

    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == origem


def test_recusa_tambem_e_legivel_pela_origem_do_frontend(api):
    """Sem isso, o navegador esconde o 401 e o frontend não sabe que deve voltar ao login."""
    origem = variavel("ENDERECO_DO_FRONTEND")

    resposta = pedir_eu(api, origem=origem)

    assert resposta.status_code == 401
    assert resposta.headers["access-control-allow-origin"] == origem


def test_outra_origem_nao_passa_pela_consulta_previa(api):
    resposta = consulta_previa(api, ORIGEM_ESTRANHA)

    assert "access-control-allow-origin" not in resposta.headers


def test_outra_origem_nao_le_a_resposta_de_eu(api):
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))

    resposta = pedir_eu(api, token, origem=ORIGEM_ESTRANHA)

    assert "access-control-allow-origin" not in resposta.headers
