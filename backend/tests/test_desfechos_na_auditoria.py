"""Todo desfecho de uma chamada fica na auditoria, e as respostas continuam as da 4a (RF-31, RS-08).

O servidor é criado pela fábrica, dentro do processo, confiando numa chave local, e grava na
auditoria do ambiente. Cada token tem um usuário novo, e o teste lê a última linha dele com a
credencial do dono.
"""

import uuid

import pytest
from apoio import banco_local, ultima_chamada_de
from chaves_locais import ChavesLocais, assinar, conteudo_valido, nova_chave
from cliente_mcp import (
    ERRO_INTERNO,
    FERRAMENTA_DESCONHECIDA,
    INDISPONIVEL,
    PARAMETRO_INVALIDO,
    assert_recusado,
    chamar,
    chamar_pelo_protocolo,
    listar_ferramentas,
    texto_do_erro,
)
from provedor import DESTINATARIO_DO_MCP
from starlette.testclient import TestClient

from acesso import Perfil
from auditoria import AuditoriaIndisponivel
from consultas import BancoDeDados, ExecutorDeConsultas, credenciais_do_ambiente

CHAVE = nova_chave()
FERRAMENTA = "vendas_indicadores"
FERRAMENTA_QUE_NUNCA_EXISTIU = "vendas_margem_por_cliente"


def token_novo(perfil: Perfil) -> tuple[str, str]:
    """Um token de um usuário que nunca chamou nada, e o identificador dele."""
    sub = str(uuid.uuid4())
    token = assinar(
        conteudo_valido(aud=DESTINATARIO_DO_MCP, sub=sub, perfil=perfil.value), CHAVE
    )
    return token, sub


@pytest.fixture
def mcp(criar_mcp):
    return criar_mcp(chaves=ChavesLocais(CHAVE))


@pytest.mark.parametrize("ferramenta", [FERRAMENTA, FERRAMENTA_QUE_NUNCA_EXISTIU])
def test_outro_perfil_e_nome_inexistente_ficam_como_negada_com_o_nome_pedido(mcp, ferramenta):
    token, sub = token_novo(Perfil.PRODUTOS)

    resultado = chamar(mcp, token, ferramenta, {"periodo": "30d"})

    assert texto_do_erro(resultado) == FERRAMENTA_DESCONHECIDA
    linha = ultima_chamada_de(sub)
    assert linha is not None
    assert linha["perfil"] == "produtos"
    assert linha["ferramenta"] == ferramenta
    assert linha["parametros"] == {"periodo": "30d"}
    assert linha["resultado"] == "negada"


@pytest.mark.parametrize(
    "argumentos",
    [
        {"periodo": "7d"},
        {"periodo": "12m", "filtro": "lojista_id = 1"},
        {"periodo": ["12m", "30d"]},
        {"periodo": None},
        {"perfil": "diretoria"},
    ],
    ids=str,
)
def test_parametro_invalido_fica_registrado_exatamente_como_chegou(mcp, argumentos):
    token, sub = token_novo(Perfil.VENDAS)

    resultado = chamar(mcp, token, FERRAMENTA, argumentos)

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO
    linha = ultima_chamada_de(sub)
    assert linha["ferramenta"] == FERRAMENTA
    assert linha["parametros"] == argumentos
    assert linha["resultado"] == "parametro_invalido"


class _ExecutorQueQuebra(ExecutorDeConsultas):
    """Autoriza como o de verdade, mas toda consulta lança uma exceção que ninguém previu."""

    def executar(self, usuario, consulta, **parametros):
        raise RuntimeError("detalhe interno")


def _sem_banco() -> ExecutorDeConsultas:
    """Um executor apontado para uma porta onde nada escuta: a consulta falha."""
    banco = BancoDeDados(host="127.0.0.1", porta=9, nome=banco_local().nome)
    return ExecutorDeConsultas(banco, credenciais_do_ambiente())


def _que_quebra() -> ExecutorDeConsultas:
    return _ExecutorQueQuebra(banco_local(), credenciais_do_ambiente())


@pytest.mark.parametrize(
    ("executor", "mensagem"),
    [(_sem_banco, INDISPONIVEL), (_que_quebra, ERRO_INTERNO)],
    ids=["consulta-falhou", "erro-interno"],
)
def test_consulta_que_falhou_e_erro_interno_ficam_como_falha(criar_mcp, executor, mensagem):
    token, sub = token_novo(Perfil.VENDAS)
    with executor() as consultas:
        mcp = criar_mcp(consultas=consultas, chaves=ChavesLocais(CHAVE))

        resultado = chamar(mcp, token, FERRAMENTA, {"periodo": "30d"})

    assert texto_do_erro(resultado) == mensagem
    linha = ultima_chamada_de(sub)
    assert linha["parametros"] == {"periodo": "30d"}
    assert linha["resultado"] == "falha"


LIMITE_DOS_PARAMETROS_EM_BYTES = 4 * 1024


@pytest.mark.parametrize("letra", ["a", "ç"], ids=["ascii", "multibyte"])
def test_argumentos_grandes_sao_cortados_e_marcados(mcp, letra):
    token, sub = token_novo(Perfil.VENDAS)
    argumentos = {"periodo": letra * 10_000}

    resultado = chamar(mcp, token, FERRAMENTA, argumentos)

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO
    linha = ultima_chamada_de(sub)
    assert linha["parametros_cortados"] is True
    assert linha["resultado"] == "parametro_invalido"
    # O corte guarda o começo do que chegou, como texto, até o limite.
    cortados = linha["parametros"]
    assert isinstance(cortados, str)
    assert cortados.startswith('{"periodo": "' + letra * 100)
    assert len(cortados.encode()) <= LIMITE_DOS_PARAMETROS_EM_BYTES
    assert len(cortados.encode()) > LIMITE_DOS_PARAMETROS_EM_BYTES - 4


def test_nome_grande_de_ferramenta_e_cortado(mcp):
    token, sub = token_novo(Perfil.VENDAS)
    nome = "vendas_" + "x" * 10_000

    resultado = chamar(mcp, token, nome, {})

    assert texto_do_erro(resultado) == FERRAMENTA_DESCONHECIDA
    linha = ultima_chamada_de(sub)
    assert linha["resultado"] == "negada"
    assert nome.startswith(linha["ferramenta"])
    assert "vendas_xxxx" in linha["ferramenta"]
    assert len(linha["ferramenta"]) < 1_000


def test_listar_as_ferramentas_nao_gera_linha(mcp):
    token, sub = token_novo(Perfil.VENDAS)

    assert listar_ferramentas(mcp, token)
    assert ultima_chamada_de(sub) is None


def test_pedido_recusado_no_token_nao_gera_linha(mcp):
    """Sem token aceito não há usuário conhecido: a recusa fica só no log."""
    sub = str(uuid.uuid4())
    de_outra_chave = assinar(
        conteudo_valido(aud=DESTINATARIO_DO_MCP, sub=sub, perfil="vendas"), nova_chave()
    )
    with TestClient(mcp) as http:
        resposta = chamar_pelo_protocolo(http, de_outra_chave, FERRAMENTA, {"periodo": "30d"})

    assert_recusado(resposta)
    assert ultima_chamada_de(sub) is None


class _AuditoriaQueFalha:
    """Uma auditoria que nunca consegue gravar."""

    def registrar(self, usuario, ferramenta, argumentos, resultado, horario):
        raise AuditoriaIndisponivel("auditoria fora do ar")


@pytest.mark.parametrize(
    ("ferramenta", "argumentos"),
    [(FERRAMENTA, {"periodo": "30d"}), (FERRAMENTA, {"periodo": "7d"}), ("inexistente", {})],
    ids=["permitida", "parametro-invalido", "negada"],
)
def test_sem_auditoria_a_chamada_e_recusada_com_servico_indisponivel(
    criar_mcp, caplog, ferramenta, argumentos
):
    """Nem a consulta que deu certo é respondida sem registro (ADR 0008)."""
    mcp = criar_mcp(auditoria=_AuditoriaQueFalha(), chaves=ChavesLocais(CHAVE))
    token, _ = token_novo(Perfil.VENDAS)

    resultado = chamar(mcp, token, ferramenta, argumentos)

    assert texto_do_erro(resultado) == INDISPONIVEL
    assert "auditoria fora do ar" in caplog.text
