"""As rotas do painel de Vendas: só o perfil Vendas lê, os outros recebem a mesma negação.

A ordem das verificações é fixa: token (401), perfil (403), parâmetros (400), consulta (RS-08).
"""

import pytest
from apoio import banco_local
from recusa import (
    RESPOSTA_DE_INDISPONIVEL,
    RESPOSTA_DE_PARAMETRO_INVALIDO,
    ROTAS_DE_VENDAS,
    assert_negado,
    assert_recusado,
    pedir,
)

from acesso import Perfil
from consultas import BancoDeDados, Credencial, ExecutorDeConsultas, credenciais_do_ambiente

OUTROS_PERFIS = [perfil for perfil in Perfil if perfil is not Perfil.VENDAS]


@pytest.fixture
def executor_sem_banco():
    """Um executor com as credenciais do ambiente, apontado para uma porta onde nada escuta."""
    banco = BancoDeDados(host="127.0.0.1", porta=9, nome=banco_local().nome)
    with ExecutorDeConsultas(banco, credenciais_do_ambiente()) as executor:
        yield executor


@pytest.mark.parametrize("rota", ROTAS_DE_VENDAS)
def test_vendas_le_cada_rota_de_vendas(api, token_de, rota):
    resposta = pedir(api, rota, token_de(Perfil.VENDAS))

    assert resposta.status_code == 200


@pytest.mark.parametrize("rota", ROTAS_DE_VENDAS)
@pytest.mark.parametrize("perfil", OUTROS_PERFIS, ids=str)
def test_outros_perfis_recebem_a_mesma_negacao_em_toda_rota_de_vendas(api, token_de, rota, perfil):
    assert_negado(pedir(api, rota, token_de(perfil)))


@pytest.mark.parametrize("rota", ROTAS_DE_VENDAS)
def test_sem_token_e_recusado_mesmo_com_parametro_invalido(api, rota):
    assert_recusado(pedir(api, rota, periodo="7d"))


@pytest.mark.parametrize("rota", ROTAS_DE_VENDAS)
@pytest.mark.parametrize("perfil", OUTROS_PERFIS, ids=str)
def test_outro_perfil_e_negado_antes_de_validar_o_parametro(api, token_de, rota, perfil):
    assert_negado(pedir(api, rota, token_de(perfil), periodo="7d", filtro="x"))


PARAMETROS_INVALIDOS = [
    {"periodo": "7d"},
    {"periodo": ""},
    {"periodo": "12M"},
    {"periodo": "dados_de_origem.cliente"},
    {"periodo": "12m", "filtro": "lojista_id = 1"},
    {"periodo": ["12m", "30d"]},
]


@pytest.mark.parametrize("rota", ROTAS_DE_VENDAS)
@pytest.mark.parametrize("parametros", PARAMETROS_INVALIDOS, ids=str)
def test_parametro_invalido_recebe_resposta_generica_sem_eco(api, token_de, rota, parametros):
    resposta = pedir(api, rota, token_de(Perfil.VENDAS), **parametros)

    assert resposta.status_code == 400
    assert resposta.json() == RESPOSTA_DE_PARAMETRO_INVALIDO


@pytest.mark.parametrize("rota", ROTAS_DE_VENDAS)
@pytest.mark.parametrize("periodo", ["30d", "90d", "12m", "24m"])
def test_cada_periodo_da_enumeracao_e_aceito(api, token_de, rota, periodo):
    assert pedir(api, rota, token_de(Perfil.VENDAS), periodo=periodo).status_code == 200


@pytest.mark.parametrize("perfil", OUTROS_PERFIS, ids=str)
def test_outro_perfil_e_negado_sem_conectar_ao_banco(
    criar_api, executor_sem_banco, token_de, perfil
):
    api = criar_api(consultas=executor_sem_banco)

    assert_negado(pedir(api, ROTAS_DE_VENDAS[0], token_de(perfil)))


def test_perfil_sem_credencial_configurada_e_negado(criar_api, token_de):
    """Um perfil cujo papel não tem senha no ambiente não ganha acesso por acidente."""
    sem_vendas = {p: c for p, c in credenciais_do_ambiente().items() if p is not Perfil.VENDAS}
    with ExecutorDeConsultas(banco_local(), sem_vendas) as executor:
        api = criar_api(consultas=executor)

        assert_negado(pedir(api, ROTAS_DE_VENDAS[0], token_de(Perfil.VENDAS)))


def test_banco_fora_do_ar_vira_falha_generica(criar_api, executor_sem_banco, token_de, caplog):
    api = criar_api(consultas=executor_sem_banco)

    resposta = pedir(api, ROTAS_DE_VENDAS[0], token_de(Perfil.VENDAS))

    assert resposta.status_code == 503
    assert resposta.json() == RESPOSTA_DE_INDISPONIVEL
    assert "consulta falhou" in caplog.text


def test_erro_do_banco_nao_chega_ao_cliente_com_nomes_internos(criar_api, token_de):
    """A senha errada faz o banco responder com o nome do papel; a API não o repassa."""
    errada = {Perfil.VENDAS: Credencial(papel="vendas", senha="senha-errada")}
    with ExecutorDeConsultas(banco_local(), errada) as executor:
        api = criar_api(consultas=executor)

        resposta = pedir(api, ROTAS_DE_VENDAS[0], token_de(Perfil.VENDAS))

    assert resposta.status_code == 503
    assert resposta.json() == RESPOSTA_DE_INDISPONIVEL
