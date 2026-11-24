"""GET /eu: a API reconhece o usuário e o perfil pelo token (RF-07, RS-01 a RS-03)."""

import jwt
import pytest
from provedor import (
    USUARIOS_DE_DEMONSTRACAO,
    LoginRecusado,
    senha_de,
    token_de_outro_servico,
    token_pelo_fluxo_de_codigo,
)
from recusa import assert_recusado, pedir_eu

from acesso import ChavesDoProvedor


@pytest.mark.parametrize("demonstracao", USUARIOS_DE_DEMONSTRACAO, ids=lambda u: u.nome_de_usuario)
def test_usuario_de_demonstracao_ve_o_proprio_nome_e_perfil(api, demonstracao):
    token = token_pelo_fluxo_de_codigo(demonstracao.nome_de_usuario, demonstracao.senha())

    resposta = pedir_eu(api, token)

    assert resposta.status_code == 200
    assert resposta.json() == {"nome": demonstracao.nome, "perfil": demonstracao.perfil.value}


def test_requisicao_sem_token_e_recusada(api):
    assert_recusado(pedir_eu(api))


@pytest.mark.parametrize(
    "autorizacao",
    [
        "",
        "Bearer",
        "Bearer ",
        "Basic YW5hOnNlbmhh",
        "Token abc",
        "Bearer nao-e-um-jwt",
        "Bearer a.b.c",
    ],
)
def test_cabecalho_mal_formado_ou_token_que_nao_e_jwt_e_recusado(api, autorizacao):
    assert_recusado(api.get("/eu", headers={"Authorization": autorizacao}))


def test_token_do_mesmo_provedor_emitido_para_outro_servico_e_recusado(api):
    token = token_de_outro_servico("ana.vendas", senha_de("ana.vendas"))

    assert_recusado(pedir_eu(api, token))


def test_token_real_vencido_e_recusado(criar_api):
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))
    vencimento = jwt.decode(token, options={"verify_signature": False})["exp"]
    api = criar_api(relogio=lambda: vencimento + 60)

    assert_recusado(pedir_eu(api, token))


def test_token_real_dentro_da_validade_e_aceito_pelo_mesmo_relogio(criar_api):
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))
    vencimento = jwt.decode(token, options={"verify_signature": False})["exp"]
    api = criar_api(relogio=lambda: vencimento - 60)

    assert pedir_eu(api, token).status_code == 200


def test_provedor_fora_do_ar_nao_e_confundido_com_token_invalido(criar_api):
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))
    # Nenhum serviço escuta na porta 9 da máquina local: as chaves não podem ser buscadas.
    api = criar_api(chaves=ChavesDoProvedor("http://127.0.0.1:9/certs"))

    resposta = pedir_eu(api, token)

    assert resposta.status_code == 503
    assert resposta.json() == {"erro": "Serviço indisponível."}
    assert "www-authenticate" not in resposta.headers


def test_senha_errada_nao_produz_token():
    with pytest.raises(LoginRecusado):
        token_pelo_fluxo_de_codigo("ana.vendas", "senha-errada")


@pytest.mark.parametrize("caminho", ["/docs", "/redoc", "/openapi.json"])
def test_a_api_nao_publica_a_propria_documentacao(api, caminho):
    """A API só serve as telas: nada de descrever as rotas a quem não está autenticado."""
    assert api.get(caminho).status_code == 404
