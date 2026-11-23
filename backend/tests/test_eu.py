"""GET /eu: a API reconhece o usuário e o perfil pelo token (RF-07, RS-01 a RS-03)."""

import jwt
import pytest
from provedor import (
    USUARIOS_DE_DEMONSTRACAO,
    senha_de,
    token_de_outro_servico,
    token_pelo_fluxo_de_codigo,
)
from recusa import assert_recusado


@pytest.mark.parametrize(
    ("usuario", "nome", "perfil"), [(u, n, p) for u, _, n, p in USUARIOS_DE_DEMONSTRACAO]
)
def test_usuario_de_demonstracao_ve_o_proprio_nome_e_perfil(cliente_da_api, usuario, nome, perfil):
    token = token_pelo_fluxo_de_codigo(usuario, senha_de(usuario))

    resposta = cliente_da_api.get("/eu", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 200
    assert resposta.json() == {"nome": nome, "perfil": perfil}


def test_requisicao_sem_token_e_recusada(cliente_da_api):
    assert_recusado(cliente_da_api.get("/eu"))


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
def test_cabecalho_mal_formado_ou_token_que_nao_e_jwt_e_recusado(cliente_da_api, autorizacao):
    assert_recusado(cliente_da_api.get("/eu", headers={"Authorization": autorizacao}))


def test_token_do_mesmo_provedor_emitido_para_outro_servico_e_recusado(cliente_da_api):
    token = token_de_outro_servico("ana.vendas", senha_de("ana.vendas"))

    assert_recusado(cliente_da_api.get("/eu", headers={"Authorization": f"Bearer {token}"}))


def test_token_real_vencido_e_recusado(criar_cliente_da_api):
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))
    vencimento = jwt.decode(token, options={"verify_signature": False})["exp"]
    cliente = criar_cliente_da_api(relogio=lambda: vencimento + 60)

    assert_recusado(cliente.get("/eu", headers={"Authorization": f"Bearer {token}"}))


def test_token_real_dentro_da_validade_e_aceito_pelo_mesmo_relogio(criar_cliente_da_api):
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"))
    vencimento = jwt.decode(token, options={"verify_signature": False})["exp"]
    cliente = criar_cliente_da_api(relogio=lambda: vencimento - 60)

    assert cliente.get("/eu", headers={"Authorization": f"Bearer {token}"}).status_code == 200
