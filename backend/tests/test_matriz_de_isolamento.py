"""A matriz de isolamento: todos os perfis contra todas as rotas de dados e todas as ferramentas.

Rotas e ferramentas são lidas dos registros (`ROTAS_DE_DADOS` da API e `FERRAMENTAS` do servidor
MCP), e o dono de cada uma é o perfil da consulta que ela serve. Uma rota ou ferramenta nova entra
na matriz sem ninguém acrescentá-la a este teste (RS-05, CA-02). Só o perfil dono lê; os demais
recebem a mesma negação genérica (RF-11, RF-22, RS-08).
"""

import httpx
import pytest
from apoio import ultima_chamada_de
from cliente_mcp import (
    FERRAMENTA_DESCONHECIDA,
    MCP_DO_AMBIENTE,
    chamar,
    chamar_pelo_protocolo,
    listar_ferramentas,
)
from provedor import conteudo
from recusa import assert_negado, pedir

from acesso import Perfil
from api.aplicacao import ROTAS_DE_DADOS
from servidor_mcp.ferramentas import FERRAMENTAS

FERRAMENTA_QUE_NUNCA_EXISTIU = "vendas_margem_por_cliente"

DONO_DA_ROTA = {rota: consulta.perfil for rota, consulta in ROTAS_DE_DADOS.items()}
DONO_DA_FERRAMENTA = {nome: ferramenta.consulta.perfil for nome, ferramenta in FERRAMENTAS.items()}


def _pares(donos: dict[str, Perfil], *, do_dono: bool) -> list:
    """Cada item do registro com cada perfil: só os pares do dono, ou só os dos demais."""
    return [
        pytest.param(item, perfil, id=f"{perfil}-{item}")
        for item in sorted(donos)
        for perfil in Perfil
        if (perfil is donos[item]) == do_dono
    ]


def _argumentos_minimos(nome: str) -> dict[str, str]:
    """Os argumentos obrigatórios da ferramenta, cada um com o primeiro valor da enumeração."""
    return {
        parametro.nome: next(iter(parametro.enumeracao)).value
        for parametro in FERRAMENTAS[nome].parametros
        if parametro.padrao is None
    }


# --- Rotas da API ---


@pytest.mark.parametrize(("rota", "perfil"), _pares(DONO_DA_ROTA, do_dono=True))
def test_o_dono_le_a_rota(api, token_de, rota, perfil):
    assert pedir(api, rota, token_de(perfil)).status_code == 200


@pytest.mark.parametrize(("rota", "perfil"), _pares(DONO_DA_ROTA, do_dono=False))
def test_quem_nao_e_dono_recebe_a_mesma_negacao_na_rota(api, token_de, rota, perfil):
    assert_negado(pedir(api, rota, token_de(perfil)))


@pytest.mark.parametrize(("rota", "perfil"), _pares(DONO_DA_ROTA, do_dono=False))
def test_quem_nao_e_dono_e_negado_antes_de_validar_o_parametro(api, token_de, rota, perfil):
    assert_negado(pedir(api, rota, token_de(perfil), periodo="7d", filtro="x"))


# --- Ferramentas do servidor MCP ---


@pytest.fixture
def mcp_do_ambiente():
    """Um cliente HTTP cru apontado para o servidor MCP do compose."""
    with httpx.Client(base_url=MCP_DO_AMBIENTE, timeout=10) as http:
        yield http


def _id_da_ultima_linha(token: str) -> int | None:
    linha = ultima_chamada_de(conteudo(token)["sub"])
    return linha["id"] if linha else None


def _assert_auditada(token: str, ferramenta: str, argumentos: dict, resultado: str) -> None:
    """A última linha da auditoria do usuário do token é a chamada que o teste acabou de fazer."""
    linha = ultima_chamada_de(conteudo(token)["sub"])
    assert linha is not None
    assert linha["perfil"] == conteudo(token)["perfil"]
    assert linha["ferramenta"] == ferramenta
    assert linha["parametros"] == argumentos
    assert linha["resultado"] == resultado


@pytest.mark.parametrize("perfil", list(Perfil), ids=str)
def test_cada_perfil_lista_so_as_ferramentas_que_sao_dele(token_de, perfil):
    token = token_de(perfil)
    antes = _id_da_ultima_linha(token)

    listadas = listar_ferramentas(MCP_DO_AMBIENTE, token)

    do_perfil = sorted(nome for nome, dono in DONO_DA_FERRAMENTA.items() if dono is perfil)
    assert sorted(f.name for f in listadas) == do_perfil
    # Listar não é chamada: não gera linha na auditoria.
    assert _id_da_ultima_linha(token) == antes


@pytest.mark.parametrize(("ferramenta", "perfil"), _pares(DONO_DA_FERRAMENTA, do_dono=True))
def test_o_dono_chama_a_ferramenta(token_de, ferramenta, perfil):
    token = token_de(perfil)
    argumentos = _argumentos_minimos(ferramenta)

    resultado = chamar(MCP_DO_AMBIENTE, token, ferramenta, argumentos)

    assert not resultado.is_error
    _assert_auditada(token, ferramenta, argumentos, "permitida")


@pytest.mark.parametrize(("ferramenta", "perfil"), _pares(DONO_DA_FERRAMENTA, do_dono=False))
def test_quem_nao_e_dono_recebe_a_resposta_de_ferramenta_inexistente(
    mcp_do_ambiente, token_de, ferramenta, perfil
):
    """Byte a byte: nada na resposta HTTP diz que a ferramenta existe para outro perfil."""
    token = token_de(perfil)
    argumentos = _argumentos_minimos(ferramenta)

    de_outro_perfil = chamar_pelo_protocolo(mcp_do_ambiente, token, ferramenta, argumentos)
    _assert_auditada(token, ferramenta, argumentos, "negada")
    inexistente = chamar_pelo_protocolo(
        mcp_do_ambiente, token, FERRAMENTA_QUE_NUNCA_EXISTIU, argumentos
    )
    # O mesmo resultado na auditoria, com o nome como foi pedido; o motivo fica só no log.
    _assert_auditada(token, FERRAMENTA_QUE_NUNCA_EXISTIU, argumentos, "negada")

    assert de_outro_perfil.status_code == inexistente.status_code == 200
    assert de_outro_perfil.content == inexistente.content
    assert _sem_data(de_outro_perfil.headers) == _sem_data(inexistente.headers)
    assert FERRAMENTA_DESCONHECIDA in de_outro_perfil.text
    assert ferramenta not in de_outro_perfil.text
    assert FERRAMENTA_QUE_NUNCA_EXISTIU not in inexistente.text


def _sem_data(cabecalhos) -> dict[str, str]:
    return {nome: valor for nome, valor in cabecalhos.items() if nome != "date"}
