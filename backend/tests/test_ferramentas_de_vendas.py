"""As ferramentas de Vendas no servidor MCP do ambiente, chamadas pelo perfil Vendas.

Um cliente MCP fala o protocolo por HTTP com o serviço `mcp` do compose, com tokens reais do
provedor (RF-19 a RF-22, RF-26). Quem lista e quem chama cada ferramenta, e a negação aos demais
perfis, está na matriz de isolamento (test_matriz_de_isolamento.py).

Depois de cada chamada, o teste confere a linha da auditoria: toda chamada fica registrada, com
o desfecho (RF-30, RF-31, CA-07).
"""

import json
import os

import httpx
import pytest
from apoio import BANCO_DA_AUDITORIA, conectar_como_dono, ultima_chamada_de
from auditada import assert_auditada
from cliente_mcp import (
    MCP_DO_AMBIENTE,
    PARAMETRO_INVALIDO,
    assert_recusado,
    chamar,
    chamar_pelo_protocolo,
    pedir_ao_protocolo,
    texto_do_erro,
)
from provedor import conteudo, senha_de, token_de_outro_servico
from recusa import pedir

from acesso import Perfil

PERIODOS = ["30d", "90d", "12m", "24m"]
API_DO_AMBIENTE = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"

# Cada ferramenta de Vendas e a rota da API que serve a mesma consulta. Toda ferramenta nova do
# painel de Vendas entra aqui.
ROTA_DA_FERRAMENTA = {
    "vendas_indicadores": "/vendas/indicadores",
    "vendas_evolucao": "/vendas/evolucao",
    "vendas_situacao_das_entregas": "/vendas/situacao-das-entregas",
    "vendas_pedidos_recentes": "/vendas/pedidos-recentes",
}
# A ferramenta de atrasos não tem rota na API nem bloco no painel, e exige o agrupamento.
ARGUMENTOS_OBRIGATORIOS = {"vendas_atrasos": {"agrupamento": "rota"}}
FERRAMENTAS_DE_VENDAS = sorted([*ROTA_DA_FERRAMENTA, *ARGUMENTOS_OBRIGATORIOS])
FERRAMENTA_QUE_NUNCA_EXISTIU = "vendas_margem_por_cliente"
# O que não pode aparecer em resposta nenhuma: o cliente, identificadores e nomes internos do banco
# (esquemas, tabelas e colunas de chave).
PROIBIDOS = ("cliente", "_id", "dados_de_origem", "vendas.")


def id_da_ultima_linha(token: str) -> int | None:
    linha = ultima_chamada_de(conteudo(token)["sub"])
    return linha["id"] if linha else None


def id_da_ultima_linha_da_auditoria() -> int | None:
    with conectar_como_dono(BANCO_DA_AUDITORIA) as conexao:
        return conexao.execute("select max(id) from auditoria.chamada").fetchone()[0]


@pytest.fixture
def mcp_do_ambiente():
    """Um cliente HTTP cru apontado para o servidor MCP do compose."""
    with httpx.Client(base_url=MCP_DO_AMBIENTE, timeout=10) as http:
        yield http


@pytest.mark.parametrize("ferramenta", sorted(ROTA_DA_FERRAMENTA))
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
    assert_auditada(token, ferramenta, {"periodo": periodo}, "permitida")


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_VENDAS)
@pytest.mark.parametrize("periodo", PERIODOS)
def test_nenhuma_resposta_traz_identificador_de_cliente_nem_nome_interno_de_banco(
    token_de, conexao_dono, ferramenta, periodo
):
    argumentos = {**ARGUMENTOS_OBRIGATORIOS.get(ferramenta, {}), "periodo": periodo}
    token = token_de(Perfil.VENDAS)

    resultado = chamar(MCP_DO_AMBIENTE, token, ferramenta, argumentos)

    assert not resultado.is_error
    assert_auditada(token, ferramenta, argumentos, "permitida")
    texto = _texto_inteiro(resultado)
    for proibido in PROIBIDOS:
        assert proibido not in texto
    for dado in _dados_pessoais_dos_clientes(conexao_dono, resultado.structured_content):
        assert str(dado) not in texto


def _texto_inteiro(resultado) -> str:
    """Tudo o que a resposta leva a quem chamou: o conteúdo estruturado e os blocos de texto."""
    estruturado = json.dumps(resultado.structured_content, ensure_ascii=False)
    return estruturado + "".join(bloco.text for bloco in resultado.content)


def _dados_pessoais_dos_clientes(conexao_dono, conteudo: dict) -> list:
    """Nome, e-mail, CPF e endereço dos clientes dos pedidos que a resposta cita, lidos
    nos dados de origem com o papel dono. Vazio para as respostas que não citam pedidos."""
    numeros = [pedido["numero"] for pedido in conteudo.get("pedidos", [])]
    if not numeros:
        return []
    linhas = conexao_dono.execute(
        """
        select c.nome, c.email, c.cpf, c.endereco
        from dados_de_origem.pedido p
        join dados_de_origem.cliente c on c.id = p.cliente_id
        where p.id = any(%s)
        """,
        (numeros,),
    ).fetchall()
    assert linhas
    return [dado for linha in linhas for dado in linha]


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_VENDAS)
def test_toda_resposta_traz_as_datas_do_periodo_usado(token_de, ferramenta):
    argumentos = {**ARGUMENTOS_OBRIGATORIOS.get(ferramenta, {}), "periodo": "30d"}
    token = token_de(Perfil.VENDAS)

    resultado = chamar(MCP_DO_AMBIENTE, token, ferramenta, argumentos)

    assert not resultado.is_error
    assert_auditada(token, ferramenta, argumentos, "permitida")
    assert resultado.structured_content["periodo"] == {"inicio": "2026-11-01", "fim": "2026-11-30"}


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_VENDAS)
def test_sem_periodo_a_ferramenta_usa_os_ultimos_12_meses(token_de, ferramenta):
    token = token_de(Perfil.VENDAS)

    obrigatorios = ARGUMENTOS_OBRIGATORIOS.get(ferramenta, {})

    sem_periodo = chamar(MCP_DO_AMBIENTE, token, ferramenta, obrigatorios)
    com_12_meses = chamar(MCP_DO_AMBIENTE, token, ferramenta, {**obrigatorios, "periodo": "12m"})

    assert not sem_periodo.is_error
    assert sem_periodo.structured_content == com_12_meses.structured_content


def test_ferramenta_inexistente_tem_o_mesmo_erro_para_vendas(mcp_do_ambiente, token_de):
    """Quem tem ferramentas também não descobre, pelo erro, nomes de outras."""
    token = token_de(Perfil.VENDAS)
    de_vendas = chamar_pelo_protocolo(mcp_do_ambiente, token, FERRAMENTA_QUE_NUNCA_EXISTIU)
    assert_auditada(token, FERRAMENTA_QUE_NUNCA_EXISTIU, None, "negada")
    de_outro = chamar_pelo_protocolo(
        mcp_do_ambiente, token_de(Perfil.PRODUTOS), FERRAMENTA_QUE_NUNCA_EXISTIU
    )

    assert de_vendas.content == de_outro.content


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_VENDAS)
def test_parametro_fora_do_previsto_e_recusado_sem_eco(token_de, ferramenta):
    argumentos = {**ARGUMENTOS_OBRIGATORIOS.get(ferramenta, {}), "periodo": "7d"}
    token = token_de(Perfil.VENDAS)

    resultado = chamar(MCP_DO_AMBIENTE, token, ferramenta, argumentos)

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO
    assert_auditada(token, ferramenta, argumentos, "parametro_invalido")


@pytest.mark.parametrize("agrupamento", ["rota", "lojista"])
def test_vendas_chama_os_atrasos_nos_dois_agrupamentos(token_de, agrupamento):
    """Os valores são conferidos com os dados de origem em test_atrasos_de_vendas.py."""
    token = token_de(Perfil.VENDAS)

    resultado = chamar(MCP_DO_AMBIENTE, token, "vendas_atrasos", {"agrupamento": agrupamento})

    assert not resultado.is_error
    assert_auditada(token, "vendas_atrasos", {"agrupamento": agrupamento}, "permitida")
    assert resultado.structured_content["agrupamento"] == agrupamento
    assert resultado.structured_content["grupos"]


@pytest.mark.parametrize("argumentos", [{}, {"agrupamento": "categoria"}], ids=str)
def test_atrasos_sem_agrupamento_valido_e_recusado_sem_eco(token_de, argumentos):
    token = token_de(Perfil.VENDAS)

    resultado = chamar(MCP_DO_AMBIENTE, token, "vendas_atrasos", argumentos)

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO
    assert_auditada(token, "vendas_atrasos", argumentos, "parametro_invalido")


def test_argumentos_grandes_sao_cortados_e_marcados_na_auditoria(token_de):
    token = token_de(Perfil.VENDAS)
    argumentos = {"periodo": "a" * 10_000}

    resultado = chamar(MCP_DO_AMBIENTE, token, "vendas_indicadores", argumentos)

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO
    linha = ultima_chamada_de(conteudo(token)["sub"])
    assert linha["ferramenta"] == "vendas_indicadores"
    assert linha["resultado"] == "parametro_invalido"
    assert linha["parametros_cortados"] is True
    # Guardado como texto, o começo do que chegou, até 4 KB.
    assert isinstance(linha["parametros"], str)
    assert linha["parametros"].startswith('{"periodo": "' + "a" * 100)
    assert len(linha["parametros"].encode()) <= 4 * 1024


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


def test_token_real_emitido_para_outro_servico_e_recusado_com_401(mcp_do_ambiente):
    """Mesmo provedor, mesmo usuário, assinatura válida: sem `pulso-mcp` entre os destinatários,
    o token não entra (RS-02)."""
    token = token_de_outro_servico("ana.vendas", senha_de("ana.vendas"))
    # O token de outro serviço não traz `sub`: confere a última linha da auditoria inteira.
    antes = id_da_ultima_linha_da_auditoria()

    assert_recusado(pedir_ao_protocolo(mcp_do_ambiente, token, "tools/list"))
    assert_recusado(chamar_pelo_protocolo(mcp_do_ambiente, token, "vendas_indicadores"))
    # A recusa no token não gera linha na auditoria: fica só no log do serviço.
    assert id_da_ultima_linha_da_auditoria() == antes


def test_o_servidor_responde_sem_sessao(mcp_do_ambiente, token_de):
    """Sem estado (RF-26): um pedido solto, sem iniciar sessão, é respondido, e nenhuma sessão
    é aberta para os próximos."""
    resposta = pedir_ao_protocolo(mcp_do_ambiente, token_de(Perfil.VENDAS), "tools/list")

    assert resposta.status_code == 200
    assert sorted(f["name"] for f in resposta.json()["result"]["tools"]) == FERRAMENTAS_DE_VENDAS
    assert "mcp-session-id" not in resposta.headers


def test_a_verificacao_de_saude_responde_sem_token(mcp_do_ambiente):
    assert mcp_do_ambiente.get("/saude").status_code == 200
