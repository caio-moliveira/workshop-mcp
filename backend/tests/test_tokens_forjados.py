"""Tokens que o provedor real não emite: a API os recusa (RS-01, RS-03, RS-08).

A API confia numa chave local; cada teste muda uma única coisa num token que seria aceito.
"""

import base64
import json
import logging
import time

import jwt
import pytest
from chaves_locais import ChavesLocais, assinar, conteudo_valido, nova_chave
from provedor import APLICACAO, DESTINATARIO_DA_API
from recusa import assert_recusado, pedir_eu

CHAVE = nova_chave()


@pytest.fixture
def api(criar_api):
    return criar_api(chaves=ChavesLocais(CHAVE))


def test_token_assinado_pela_chave_confiavel_e_aceito(api):
    resposta = pedir_eu(api, assinar(conteudo_valido(), CHAVE))

    assert resposta.status_code == 200
    assert resposta.json() == {"nome": "Ana Ribeiro", "perfil": "vendas"}


@pytest.mark.parametrize(
    "perfil",
    [None, "", "Vendas", "administrador", ["vendas"], ["vendas", "produtos"], 1],
    ids=["ausente", "vazio", "maiusculo", "desconhecido", "lista", "dois", "numero"],
)
def test_token_sem_exatamente_um_perfil_conhecido_e_recusado(api, perfil):
    assert_recusado(pedir_eu(api, assinar(conteudo_valido(perfil=perfil), CHAVE)))


@pytest.mark.parametrize("claim", ["iss", "aud", "sub", "exp", "name"])
def test_token_sem_claim_obrigatoria_e_recusado(api, claim):
    assert_recusado(pedir_eu(api, assinar(conteudo_valido(**{claim: None}), CHAVE)))


def test_token_assinado_por_outra_chave_e_recusado(api):
    assert_recusado(pedir_eu(api, assinar(conteudo_valido(), nova_chave())))


def _sem_assinatura(conteudo: dict) -> str:
    def parte(dados: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(dados).encode()).rstrip(b"=").decode()

    return f"{parte({'alg': 'none', 'typ': 'JWT'})}.{parte(conteudo)}."


def test_token_sem_assinatura_e_recusado(api):
    assert_recusado(pedir_eu(api, _sem_assinatura(conteudo_valido())))


def test_token_com_assinatura_simetrica_e_recusado(api):
    segredo = "um-segredo-compartilhado-qualquer-32b"
    token = jwt.encode(conteudo_valido(), segredo, algorithm="HS256")

    assert_recusado(pedir_eu(api, token))


def test_token_de_outro_emissor_e_recusado(api):
    conteudo = conteudo_valido(iss="http://localhost:8080/realms/outro")

    assert_recusado(pedir_eu(api, assinar(conteudo, CHAVE)))


@pytest.mark.parametrize("destinatario", ["outra-api", APLICACAO, ["account"]])
def test_token_para_outro_destinatario_e_recusado(api, destinatario):
    assert_recusado(pedir_eu(api, assinar(conteudo_valido(aud=destinatario), CHAVE)))


def test_token_com_a_api_entre_varios_destinatarios_e_aceito(api):
    conteudo = conteudo_valido(aud=["account", DESTINATARIO_DA_API])

    assert pedir_eu(api, assinar(conteudo, CHAVE)).status_code == 200


def test_token_que_ainda_nao_vale_e_recusado(api):
    agora = int(time.time())
    conteudo = conteudo_valido(nbf=agora + 600, iat=agora + 600, exp=agora + 900)

    assert_recusado(pedir_eu(api, assinar(conteudo, CHAVE)))


@pytest.mark.parametrize("campo", ["exp", "nbf"])
def test_token_com_data_que_nao_e_numero_e_recusado(api, campo):
    assert_recusado(pedir_eu(api, assinar(conteudo_valido(**{campo: "amanhã"}), CHAVE)))


def test_motivo_da_recusa_vai_para_o_log_sem_o_token(api, caplog):
    token = assinar(conteudo_valido(perfil="administrador"), CHAVE)

    with caplog.at_level(logging.WARNING):
        assert_recusado(pedir_eu(api, token))

    assert "perfil" in caplog.text
    assert token not in caplog.text


def test_perfil_enviado_por_quem_chama_nao_muda_o_perfil_do_token(api):
    token = assinar(conteudo_valido(perfil="vendas"), CHAVE)

    resposta = api.get(
        "/eu",
        params={"perfil": "diretoria"},
        headers={"Authorization": f"Bearer {token}", "X-Perfil": "diretoria"},
    )

    assert resposta.json()["perfil"] == "vendas"
