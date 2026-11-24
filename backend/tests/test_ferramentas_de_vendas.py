"""As ferramentas de Vendas no servidor MCP do ambiente: só o perfil Vendas as lista e chama.

Um cliente MCP fala o protocolo por HTTP com o serviço `mcp` do compose, com tokens reais do
provedor (RF-19 a RF-22, RF-26, CA-02). Os outros perfis recebem a lista vazia e, na chamada
direta, o mesmo erro de uma ferramenta que não existe (RS-08).
"""

import os

import httpx
import pytest
from cliente_mcp import (
    FERRAMENTA_DESCONHECIDA,
    MCP_DO_AMBIENTE,
    PARAMETRO_INVALIDO,
    assert_recusado,
    chamar,
    chamar_pelo_protocolo,
    listar_ferramentas,
    pedir_ao_protocolo,
    texto_do_erro,
)
from recusa import pedir

from acesso import Perfil

OUTROS_PERFIS = [perfil for perfil in Perfil if perfil is not Perfil.VENDAS]
PERIODOS = ["30d", "90d", "12m", "24m"]
API_DO_AMBIENTE = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"

# Cada ferramenta de Vendas e a rota da API que serve a mesma consulta. Toda ferramenta nova do
# painel de Vendas entra aqui.
ROTA_DA_FERRAMENTA = {
    "vendas_indicadores": "/vendas/indicadores",
}
FERRAMENTAS_DE_VENDAS = sorted(ROTA_DA_FERRAMENTA)
FERRAMENTA_QUE_NUNCA_EXISTIU = "vendas_margem_por_cliente"


@pytest.fixture
def mcp_do_ambiente():
    """Um cliente HTTP cru apontado para o servidor MCP do compose."""
    with httpx.Client(base_url=MCP_DO_AMBIENTE, timeout=10) as http:
        yield http


def test_vendas_lista_as_ferramentas_de_vendas(token_de):
    ferramentas = listar_ferramentas(MCP_DO_AMBIENTE, token_de(Perfil.VENDAS))

    assert sorted(f.name for f in ferramentas) == FERRAMENTAS_DE_VENDAS


@pytest.mark.parametrize("perfil", OUTROS_PERFIS, ids=str)
def test_outros_perfis_recebem_a_lista_vazia(token_de, perfil):
    assert listar_ferramentas(MCP_DO_AMBIENTE, token_de(perfil)) == []


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_VENDAS)
@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_conteudo_da_rota_da_api(token_de, ferramenta, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    token = token_de(Perfil.VENDAS)
    with httpx.Client(base_url=API_DO_AMBIENTE, timeout=10) as api:
        da_api = pedir(api, ROTA_DA_FERRAMENTA[ferramenta], token, periodo=periodo)

    resultado = chamar(MCP_DO_AMBIENTE, token, ferramenta, {"periodo": periodo})

    assert da_api.status_code == 200
    assert not resultado.is_error
    assert resultado.structured_content == da_api.json()


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_VENDAS)
def test_sem_periodo_a_ferramenta_usa_os_ultimos_12_meses(token_de, ferramenta):
    token = token_de(Perfil.VENDAS)

    sem_periodo = chamar(MCP_DO_AMBIENTE, token, ferramenta)

    assert not sem_periodo.is_error
    assert (
        sem_periodo.structured_content
        == chamar(MCP_DO_AMBIENTE, token, ferramenta, {"periodo": "12m"}).structured_content
    )


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_VENDAS)
@pytest.mark.parametrize("perfil", OUTROS_PERFIS, ids=str)
def test_outro_perfil_recebe_o_erro_de_ferramenta_inexistente(token_de, ferramenta, perfil):
    resultado = chamar(MCP_DO_AMBIENTE, token_de(perfil), ferramenta)

    assert texto_do_erro(resultado) == FERRAMENTA_DESCONHECIDA


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_VENDAS)
@pytest.mark.parametrize("perfil", OUTROS_PERFIS, ids=str)
def test_a_resposta_a_outro_perfil_e_identica_a_de_ferramenta_inexistente(
    mcp_do_ambiente, token_de, ferramenta, perfil
):
    """Byte a byte: nada na resposta HTTP diz que a ferramenta existe para outro perfil."""
    token = token_de(perfil)

    de_outro_perfil = chamar_pelo_protocolo(mcp_do_ambiente, token, ferramenta)
    inexistente = chamar_pelo_protocolo(mcp_do_ambiente, token, FERRAMENTA_QUE_NUNCA_EXISTIU)

    assert de_outro_perfil.status_code == inexistente.status_code == 200
    assert de_outro_perfil.content == inexistente.content
    assert _sem_data(de_outro_perfil.headers) == _sem_data(inexistente.headers)
    assert FERRAMENTA_DESCONHECIDA in de_outro_perfil.text
    assert ferramenta not in de_outro_perfil.text
    assert FERRAMENTA_QUE_NUNCA_EXISTIU not in inexistente.text


def _sem_data(cabecalhos) -> dict[str, str]:
    return {nome: valor for nome, valor in cabecalhos.items() if nome != "date"}


def test_ferramenta_inexistente_tem_o_mesmo_erro_para_vendas(mcp_do_ambiente, token_de):
    """Quem tem ferramentas também não descobre, pelo erro, nomes de outras."""
    de_vendas = chamar_pelo_protocolo(
        mcp_do_ambiente, token_de(Perfil.VENDAS), FERRAMENTA_QUE_NUNCA_EXISTIU
    )
    de_outro = chamar_pelo_protocolo(
        mcp_do_ambiente, token_de(Perfil.PRODUTOS), FERRAMENTA_QUE_NUNCA_EXISTIU
    )

    assert de_vendas.content == de_outro.content


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_VENDAS)
def test_parametro_fora_do_previsto_e_recusado_sem_eco(token_de, ferramenta):
    resultado = chamar(MCP_DO_AMBIENTE, token_de(Perfil.VENDAS), ferramenta, {"periodo": "7d"})

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO


@pytest.mark.parametrize(
    "pedido",
    [
        ("tools/list", None),
        ("tools/call", {"name": "vendas_indicadores", "arguments": {}}),
        ("tools/call", {"name": "vendas_indicadores", "arguments": {"periodo": "7d"}}),
        ("tools/call", {"name": FERRAMENTA_QUE_NUNCA_EXISTIU, "arguments": {}}),
        ("initialize", None),
    ],
    ids=["listar", "chamar", "parametro-invalido", "inexistente", "iniciar"],
)
def test_sem_token_todo_pedido_e_recusado_com_401(mcp_do_ambiente, pedido):
    """A recusa vem antes de tudo: não depende da ferramenta nem dos parâmetros (RF-06)."""
    resposta = pedir_ao_protocolo(mcp_do_ambiente, None, *pedido)

    assert_recusado(resposta)
    assert resposta.content == b""


def test_token_que_nao_veio_do_provedor_e_recusado_com_401(mcp_do_ambiente):
    assert_recusado(pedir_ao_protocolo(mcp_do_ambiente, "um-token-qualquer", "tools/list"))


def test_o_servidor_responde_sem_sessao(mcp_do_ambiente, token_de):
    """Sem estado (RF-26): um pedido solto, sem iniciar sessão, é respondido, e nenhuma sessão
    é aberta para os próximos."""
    resposta = pedir_ao_protocolo(mcp_do_ambiente, token_de(Perfil.VENDAS), "tools/list")

    assert resposta.status_code == 200
    assert [f["name"] for f in resposta.json()["result"]["tools"]] == FERRAMENTAS_DE_VENDAS
    assert "mcp-session-id" not in resposta.headers


def test_a_verificacao_de_saude_responde_sem_token(mcp_do_ambiente):
    assert mcp_do_ambiente.get("/saude").status_code == 200
