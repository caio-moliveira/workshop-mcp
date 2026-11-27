"""A rota do painel de segurança: a última execução de aceite, para os quatro perfis.

A rota só existe com o interruptor de demonstração ligado; desligado, ela responde como uma rota
inexistente e o `/eu` não a anuncia. Ela não tem dono: qualquer perfil autenticado a lê, e sem
token ela recusa, como toda rota (RS-05). O que ela devolve passa pela forma do resultado, e
nada fora dela sai: nem token, nem segredo, nem dado de negócio.
"""

import json

import pytest
from recusa import assert_recusado, pedir, pedir_eu
from registros import DONO_DA_ROTA

from aceite import ARQUIVO_DA_ULTIMA_EXECUCAO
from acesso import Perfil

# Uma execução gravada, escrita à mão na forma prevista: um cenário permitido e um negado.
EXECUCAO = {
    "executada_em": "2026-11-26T14:03:12+00:00",
    "resumo": {"executados": 2, "permitidos": 1, "negados": 1, "divergencias": 1},
    "matriz_completa": None,
    "carga": None,
    "cenarios": [
        {
            "id": "api-dono-le-a-propria-rota",
            "descricao": "O dono lê a própria rota",
            "grupo": "api",
            "quem": {"tipo": "usuario", "nome": "ana.vendas"},
            "perfil": "vendas",
            "alvo": {"tipo": "rota", "nome": "/vendas/pedidos-recentes", "parametros": {}},
            "camadas_de_defesa": ["api"],
            "esperado": "permitido",
            "obtido": "permitido",
            "divergencia": False,
            "resposta": {"status": 200, "mensagem": None, "linhas": 10},
            "auditoria": None,
            "duracao_em_ms": 41,
        },
        {
            "id": "api-vendas-le-rota-da-diretoria",
            "descricao": "Vendas lê uma rota da Diretoria",
            "grupo": "api",
            "quem": {"tipo": "usuario", "nome": "ana.vendas"},
            "perfil": "vendas",
            "alvo": {"tipo": "rota", "nome": "/diretoria/indicadores", "parametros": {}},
            "camadas_de_defesa": ["api"],
            "esperado": "negado",
            "obtido": "permitido",
            "divergencia": True,
            "resposta": {"status": 200, "mensagem": None, "linhas": 1},
            "auditoria": None,
            "duracao_em_ms": 12,
        },
    ],
}


def _gravar(pasta, conteudo: dict) -> None:
    (pasta / ARQUIVO_DA_ULTIMA_EXECUCAO).write_text(json.dumps(conteudo), encoding="utf-8")


@pytest.fixture
def pasta(tmp_path):
    return tmp_path


@pytest.fixture
def api_ligada(criar_api, pasta):
    return criar_api(execucao_de_aceite=pasta)


@pytest.mark.parametrize("perfil", list(Perfil), ids=str)
def test_os_quatro_perfis_recebem_a_ultima_execucao(api_ligada, pasta, token_de, perfil):
    _gravar(pasta, EXECUCAO)

    resposta = pedir(api_ligada, "/seguranca", token_de(perfil))

    assert resposta.status_code == 200
    assert resposta.json() == {"execucao": EXECUCAO}


def test_a_nova_execucao_substitui_a_anterior(api_ligada, pasta, token_de):
    _gravar(pasta, EXECUCAO)
    pedir(api_ligada, "/seguranca", token_de(Perfil.VENDAS))
    nova = {**EXECUCAO, "executada_em": "2026-11-26T15:00:00+00:00"}
    _gravar(pasta, nova)

    resposta = pedir(api_ligada, "/seguranca", token_de(Perfil.VENDAS))

    assert resposta.json()["execucao"]["executada_em"] == "2026-11-26T15:00:00+00:00"


def test_sem_execucao_gravada_vem_o_estado_vazio(api_ligada, token_de):
    resposta = pedir(api_ligada, "/seguranca", token_de(Perfil.PRODUTOS))

    assert resposta.status_code == 200
    assert resposta.json() == {"execucao": None}


def test_sem_token_a_rota_recusa(api_ligada, pasta):
    _gravar(pasta, EXECUCAO)

    assert_recusado(pedir(api_ligada, "/seguranca"))


def test_desligado_a_rota_responde_como_uma_rota_inexistente(api, token_de):
    token = token_de(Perfil.DIRETORIA)

    painel = pedir(api, "/seguranca", token)
    inexistente = pedir(api, "/rota-que-nunca-existiu", token)

    assert painel.status_code == inexistente.status_code == 404
    assert painel.content == inexistente.content
    assert dict(painel.headers) == dict(inexistente.headers)
    # Sem token, também: nada responde 401 onde não há rota.
    assert pedir(api, "/seguranca").status_code == 404


def test_o_eu_anuncia_o_painel_so_com_o_interruptor_ligado(api, api_ligada, token_de):
    token = token_de(Perfil.COMERCIAL)

    assert pedir_eu(api_ligada, token).json()["painel_de_seguranca"] is True
    assert "painel_de_seguranca" not in pedir_eu(api, token).json()


def test_nada_fora_da_forma_do_resultado_sai_pela_rota(api_ligada, pasta, token_de):
    """Um campo a mais no arquivo, um token ou o corpo de uma resposta, não chega ao navegador."""
    token_plantado = "eyJhbGciOiJSUzI1NiJ9.plantado.assinatura"
    plantado = json.loads(json.dumps(EXECUCAO))
    plantado["token"] = token_plantado
    plantado["cenarios"][0]["quem"]["token"] = token_plantado
    plantado["cenarios"][0]["resposta"]["corpo"] = {"pedidos": [{"numero": "P-1", "valor": 9}]}
    plantado["cenarios"][0]["senha"] = "segredo"
    _gravar(pasta, plantado)

    resposta = pedir(api_ligada, "/seguranca", token_de(Perfil.VENDAS))

    assert resposta.json() == {"execucao": EXECUCAO}
    assert token_plantado not in resposta.text
    assert "segredo" not in resposta.text


def test_um_cenario_permitido_traz_so_o_status_e_as_linhas(api_ligada, pasta, token_de):
    """A mensagem é só da negação: no permitido, ela poderia carregar dado de negócio."""
    com_mensagem = json.loads(json.dumps(EXECUCAO))
    com_mensagem["cenarios"][0]["resposta"]["mensagem"] = "Receita de R$ 1.234.567,00"
    _gravar(pasta, com_mensagem)

    resposta = pedir(api_ligada, "/seguranca", token_de(Perfil.VENDAS))

    assert resposta.json() == {"execucao": EXECUCAO}
    assert "1.234.567" not in resposta.text


def test_a_rota_do_painel_nao_entra_no_registro_das_rotas_de_dados(api_ligada):
    """Sem dono, ela fica fora da matriz de isolamento, que só percorre o registro."""
    assert "/seguranca" not in DONO_DA_ROTA
    assert "/seguranca" in {rota.path for rota in api_ligada.app.routes}
