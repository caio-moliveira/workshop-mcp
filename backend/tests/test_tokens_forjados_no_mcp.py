"""Tokens que o provedor real não emite, contra o servidor MCP (RS-01, RS-02, RS-03, RS-08).

O servidor é criado pela fábrica, dentro do processo, confiando numa chave local; cada teste muda
uma única coisa num token que seria aceito. Os pedidos passam pela camada HTTP do servidor.
"""

import base64
import json
import logging
import time

import jwt
import pytest
from apoio import banco_local
from chaves_locais import ChavesLocais, assinar, conteudo_valido, nova_chave
from cliente_mcp import (
    ERRO_INTERNO,
    FERRAMENTA_DESCONHECIDA,
    INDISPONIVEL,
    PARAMETRO_INVALIDO,
    PROTOCOLO_SEM_SESSAO,
    assert_recusado,
    chamar,
    chamar_pelo_protocolo,
    listar_ferramentas,
    pedir_ao_protocolo,
    texto_do_erro,
)
from provedor import APLICACAO, DESTINATARIO_DA_API, DESTINATARIO_DO_MCP
from registros import DONO_DA_FERRAMENTA, ferramentas_de
from starlette.testclient import TestClient

from acesso import Perfil, ProvedorIndisponivel
from consultas import BancoDeDados, Credencial, ExecutorDeConsultas, credenciais_do_ambiente

CHAVE = nova_chave()
FERRAMENTA = "vendas_indicadores"
FERRAMENTA_QUE_NUNCA_EXISTIU = "vendas_margem_por_cliente"
# Os perfis que não são donos da ferramenta, lidos do registro.
OUTROS_PERFIS = [perfil for perfil in Perfil if perfil is not DONO_DA_FERRAMENTA[FERRAMENTA]]


def conteudo(**sobreposicoes) -> dict:
    """O conteúdo de um token que o servidor MCP aceitaria, com os campos trocados à vontade."""
    return conteudo_valido(**{"aud": DESTINATARIO_DO_MCP, **sobreposicoes})


def token_de(perfil: Perfil) -> str:
    return assinar(conteudo(perfil=perfil.value), CHAVE)


@pytest.fixture
def mcp(criar_mcp):
    return criar_mcp(chaves=ChavesLocais(CHAVE))


@pytest.fixture
def http(mcp):
    """Pedidos HTTP crus à aplicação do servidor MCP, iniciada para o teste."""
    with TestClient(mcp) as cliente:
        yield cliente


def recusa_de_referencia(http):
    """A resposta a um token que nem é um JWT: toda recusa precisa ser igual a ela."""
    return pedir_ao_protocolo(http, "um-token-qualquer", "tools/list")


def assert_recusa_identica(http, token: str) -> None:
    """Recusado com 401, e nada na resposta distingue o motivo (RS-08)."""
    resposta = pedir_ao_protocolo(http, token, "tools/list")
    referencia = recusa_de_referencia(http)

    assert_recusado(resposta)
    assert resposta.content == referencia.content
    assert resposta.headers == referencia.headers


def test_token_assinado_pela_chave_confiavel_e_aceito(mcp):
    ferramentas = listar_ferramentas(mcp, token_de(Perfil.VENDAS))

    assert FERRAMENTA in [f.name for f in ferramentas]


@pytest.mark.parametrize(
    "perfil",
    [None, "", "Vendas", "administrador", ["vendas"], ["vendas", "produtos"], 1],
    ids=["ausente", "vazio", "maiusculo", "desconhecido", "lista", "dois", "numero"],
)
def test_token_sem_exatamente_um_perfil_conhecido_e_recusado(http, perfil):
    assert_recusa_identica(http, assinar(conteudo(perfil=perfil), CHAVE))


@pytest.mark.parametrize("claim", ["iss", "aud", "sub", "exp", "name"])
def test_token_sem_claim_obrigatoria_e_recusado(http, claim):
    assert_recusa_identica(http, assinar(conteudo(**{claim: None}), CHAVE))


def test_token_assinado_por_outra_chave_e_recusado(http):
    assert_recusa_identica(http, assinar(conteudo(), nova_chave()))


def _sem_assinatura(conteudo_do_token: dict) -> str:
    def parte(dados: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(dados).encode()).rstrip(b"=").decode()

    return f"{parte({'alg': 'none', 'typ': 'JWT'})}.{parte(conteudo_do_token)}."


def test_token_sem_assinatura_e_recusado(http):
    assert_recusa_identica(http, _sem_assinatura(conteudo()))


def test_token_com_assinatura_simetrica_e_recusado(http):
    segredo = "um-segredo-compartilhado-qualquer-32b"

    assert_recusa_identica(http, jwt.encode(conteudo(), segredo, algorithm="HS256"))


def test_token_de_outro_emissor_e_recusado(http):
    forjado = conteudo(iss="http://localhost:8080/realms/outro")

    assert_recusa_identica(http, assinar(forjado, CHAVE))


@pytest.mark.parametrize(
    "destinatario",
    ["outra-aplicacao", APLICACAO, DESTINATARIO_DA_API, ["account"], ["account", "pulso-api"]],
    ids=str,
)
def test_token_para_outro_destinatario_e_recusado(http, destinatario):
    """Inclusive o token só da API: valer na API não é valer no servidor MCP (RS-02)."""
    assert_recusa_identica(http, assinar(conteudo(aud=destinatario), CHAVE))


def test_token_com_o_mcp_entre_varios_destinatarios_e_aceito(mcp):
    token = assinar(conteudo(aud=["account", DESTINATARIO_DA_API, DESTINATARIO_DO_MCP]), CHAVE)

    assert FERRAMENTA in [f.name for f in listar_ferramentas(mcp, token)]


def test_token_vencido_e_recusado(http):
    agora = int(time.time())
    vencido = conteudo(iat=agora - 900, nbf=agora - 900, exp=agora - 600)

    assert_recusa_identica(http, assinar(vencido, CHAVE))


def test_token_que_ainda_nao_vale_e_recusado(http):
    agora = int(time.time())
    futuro = conteudo(nbf=agora + 600, iat=agora + 600, exp=agora + 900)

    assert_recusa_identica(http, assinar(futuro, CHAVE))


@pytest.mark.parametrize("campo", ["exp", "nbf"])
def test_token_com_data_que_nao_e_numero_e_recusado(http, campo):
    assert_recusa_identica(http, assinar(conteudo(**{campo: "amanhã"}), CHAVE))


def test_token_recusado_nao_chama_ferramenta(http):
    """A recusa vem antes da ferramenta e dos parâmetros, seja qual for o pedido."""
    forjado = assinar(conteudo(), nova_chave())

    assert_recusado(chamar_pelo_protocolo(http, forjado, FERRAMENTA))
    assert_recusado(chamar_pelo_protocolo(http, forjado, FERRAMENTA, {"periodo": "7d"}))


def test_motivo_da_recusa_vai_para_o_log_sem_o_token(http, caplog):
    token = assinar(conteudo(perfil="administrador"), CHAVE)

    with caplog.at_level(logging.WARNING):
        resposta = pedir_ao_protocolo(http, token, "tools/list")

    assert_recusado(resposta)
    assert "perfil" not in resposta.text
    assert "perfil" in caplog.text
    assert token not in caplog.text


def test_provedor_fora_do_ar_e_indisponibilidade_e_nao_recusa(criar_mcp, caplog):
    class SemProvedor:
        def chave_para(self, token: str):
            raise ProvedorIndisponivel("detalhe interno: keycloak:8080 não respondeu")

    with TestClient(criar_mcp(chaves=SemProvedor())) as http:
        resposta = pedir_ao_protocolo(http, token_de(Perfil.VENDAS), "tools/list")

    assert resposta.status_code == 503
    assert resposta.json() == {"erro": INDISPONIVEL}
    assert "keycloak:8080" in caplog.text


# --- Perfil: só o do token, e antes dos parâmetros ---


@pytest.mark.parametrize("perfil", OUTROS_PERFIS, ids=str)
@pytest.mark.parametrize(
    "argumentos",
    [{}, {"periodo": "12m"}, {"periodo": "7d"}, {"filtro": "x"}, {"periodo": 5}],
    ids=str,
)
@pytest.mark.parametrize("versao", [None, PROTOCOLO_SEM_SESSAO], ids=["anterior", "sem-sessao"])
def test_outro_perfil_recebe_o_erro_de_ferramenta_inexistente_antes_dos_parametros(
    http, perfil, argumentos, versao
):
    """Ordem token → perfil → parâmetros: o parâmetro inválido de outro perfil não muda o erro,
    e a resposta é, byte a byte, a de uma ferramenta que nunca existiu. Nas duas versões do
    protocolo que o servidor fala."""
    token = token_de(perfil)

    de_outro_perfil = chamar_pelo_protocolo(http, token, FERRAMENTA, argumentos, versao)
    inexistente = chamar_pelo_protocolo(
        http, token, FERRAMENTA_QUE_NUNCA_EXISTIU, argumentos, versao
    )

    assert de_outro_perfil.status_code == 200
    assert de_outro_perfil.content == inexistente.content
    assert de_outro_perfil.headers == inexistente.headers
    erro = de_outro_perfil.json()["result"]
    assert erro["content"] == [{"type": "text", "text": FERRAMENTA_DESCONHECIDA}]
    assert erro["isError"] is True
    assert FERRAMENTA not in de_outro_perfil.text


@pytest.mark.parametrize(
    "nome", [FERRAMENTA_QUE_NUNCA_EXISTIU, "Vendas_Indicadores", "", "x" * 300]
)
def test_ferramenta_inexistente_nao_tem_o_nome_repetido_no_erro(http, nome):
    resposta = chamar_pelo_protocolo(http, token_de(Perfil.VENDAS), nome)

    assert resposta.json()["result"] == {
        "content": [{"type": "text", "text": FERRAMENTA_DESCONHECIDA}],
        "isError": True,
    }


@pytest.fixture
def executor_sem_banco():
    """Um executor com as credenciais do ambiente, apontado para uma porta onde nada escuta."""
    banco = BancoDeDados(host="127.0.0.1", porta=9, nome=banco_local().nome)
    with ExecutorDeConsultas(banco, credenciais_do_ambiente()) as executor:
        yield executor


@pytest.mark.parametrize("perfil", OUTROS_PERFIS, ids=str)
def test_outro_perfil_e_negado_sem_conectar_ao_banco(criar_mcp, executor_sem_banco, perfil):
    mcp = criar_mcp(consultas=executor_sem_banco, chaves=ChavesLocais(CHAVE))

    assert texto_do_erro(chamar(mcp, token_de(perfil), FERRAMENTA)) == FERRAMENTA_DESCONHECIDA


def test_perfil_sem_credencial_configurada_nao_ve_nem_chama_a_ferramenta(criar_mcp):
    """Um perfil cujo papel não tem senha no ambiente não ganha acesso por acidente."""
    sem_vendas = {p: c for p, c in credenciais_do_ambiente().items() if p is not Perfil.VENDAS}
    with ExecutorDeConsultas(banco_local(), sem_vendas) as executor:
        mcp = criar_mcp(consultas=executor, chaves=ChavesLocais(CHAVE))
        token = token_de(Perfil.VENDAS)

        assert listar_ferramentas(mcp, token) == []
        assert texto_do_erro(chamar(mcp, token, FERRAMENTA)) == FERRAMENTA_DESCONHECIDA


@pytest.mark.parametrize("perfil", OUTROS_PERFIS, ids=str)
def test_perfil_enviado_por_quem_chama_nao_muda_o_perfil_do_token(http, perfil):
    """RS-03: nem como argumento, nem como cabeçalho, nem na URL."""
    cabecalhos = {
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {token_de(perfil)}",
        "X-Perfil": "vendas",
    }

    def pedir(metodo: str, parametros: dict | None = None):
        corpo = {"jsonrpc": "2.0", "id": 1, "method": metodo, "params": parametros or {}}
        return http.post("/mcp?perfil=vendas", json=corpo, headers=cabecalhos).json()["result"]

    assert sorted(f["name"] for f in pedir("tools/list")["tools"]) == ferramentas_de(perfil)
    chamada = pedir("tools/call", {"name": FERRAMENTA, "arguments": {"perfil": "vendas"}})
    assert chamada["content"][0]["text"] == FERRAMENTA_DESCONHECIDA


def test_perfil_como_argumento_e_parametro_fora_do_previsto_para_vendas(mcp):
    resultado = chamar(mcp, token_de(Perfil.VENDAS), FERRAMENTA, {"perfil": "diretoria"})

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO


# --- Parâmetros e falhas: mensagens genéricas, motivo só no log ---


PARAMETROS_INVALIDOS = [
    {"periodo": "7d"},
    {"periodo": ""},
    {"periodo": "12M"},
    {"periodo": "dados_de_origem.cliente"},
    {"periodo": "12m", "filtro": "lojista_id = 1"},
    {"periodo": ["12m", "30d"]},
    {"periodo": 12},
    {"periodo": None},
    {"periodo": {"valor": "12m"}},
    {"agrupamento": "rota"},
]


@pytest.mark.parametrize("argumentos", PARAMETROS_INVALIDOS, ids=str)
def test_parametro_invalido_recebe_erro_generico_sem_eco(http, argumentos):
    resposta = chamar_pelo_protocolo(http, token_de(Perfil.VENDAS), FERRAMENTA, argumentos)

    assert resposta.json()["result"] == {
        "content": [{"type": "text", "text": PARAMETRO_INVALIDO}],
        "isError": True,
    }


@pytest.mark.parametrize("periodo", ["30d", "90d", "12m", "24m"])
def test_cada_periodo_da_enumeracao_e_aceito(mcp, periodo):
    resultado = chamar(mcp, token_de(Perfil.VENDAS), FERRAMENTA, {"periodo": periodo})

    assert not resultado.is_error
    assert set(resultado.structured_content["periodo"]) == {"inicio", "fim"}


def test_banco_fora_do_ar_e_indisponibilidade_generica(criar_mcp, executor_sem_banco, caplog):
    mcp = criar_mcp(consultas=executor_sem_banco, chaves=ChavesLocais(CHAVE))

    resultado = chamar(mcp, token_de(Perfil.VENDAS), FERRAMENTA)

    assert texto_do_erro(resultado) == INDISPONIVEL
    assert "consulta falhou" in caplog.text


def test_erro_do_banco_nao_chega_a_quem_chama_com_nomes_internos(criar_mcp):
    """A senha errada faz o banco responder com o nome do papel; o servidor não o repassa."""
    errada = {Perfil.VENDAS: Credencial(papel="vendas", senha="senha-errada")}
    with ExecutorDeConsultas(banco_local(), errada) as executor:
        mcp = criar_mcp(consultas=executor, chaves=ChavesLocais(CHAVE))

        resultado = chamar(mcp, token_de(Perfil.VENDAS), FERRAMENTA)

    assert texto_do_erro(resultado) == INDISPONIVEL


class _ExecutorQueQuebra(ExecutorDeConsultas):
    """Autoriza como o de verdade, mas toda consulta lança uma exceção que ninguém previu."""

    def executar(self, usuario, consulta, **parametros):
        raise RuntimeError("detalhe interno: vendas.pedido")


def test_erro_inesperado_e_erro_interno_generico_sem_detalhe(criar_mcp, caplog):
    with _ExecutorQueQuebra(banco_local(), credenciais_do_ambiente()) as executor:
        mcp = criar_mcp(consultas=executor, chaves=ChavesLocais(CHAVE))
        with TestClient(mcp) as http:
            resposta = chamar_pelo_protocolo(http, token_de(Perfil.VENDAS), FERRAMENTA)

    assert resposta.json()["result"] == {
        "content": [{"type": "text", "text": ERRO_INTERNO}],
        "isError": True,
    }
    assert "vendas.pedido" not in resposta.text
    assert "detalhe interno: vendas.pedido" in caplog.text
