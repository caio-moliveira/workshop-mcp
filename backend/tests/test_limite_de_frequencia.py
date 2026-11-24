"""O limite de frequência por usuário no servidor MCP (RS-11).

O servidor é criado pela fábrica, dentro do processo, com um limite baixo e um relógio falso,
para o teste avançar o tempo sem esperar. Os tokens são assinados por uma chave local: cada
usuário é um `sub` novo, e a auditoria de um teste não se mistura com a dos outros.
"""

import uuid

import pytest
from apoio import ultima_chamada_de
from chaves_locais import ChavesLocais, assinar, conteudo_valido, nova_chave
from cliente_mcp import chamar, listar_ferramentas, texto_do_erro
from provedor import DESTINATARIO_DO_MCP

from servidor_mcp import LimiteDeFrequencia, limite_do_ambiente

CHAVE = nova_chave()
FERRAMENTA = "vendas_indicadores"
LIMITADA = "Muitas chamadas em pouco tempo. Tente de novo em instantes."
JANELA = 60


class RelogioFalso:
    """Um relógio em segundos que só anda quando o teste manda."""

    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += segundos


class Usuario:
    """Um usuário de Vendas com token próprio, assinado pela chave local."""

    def __init__(self) -> None:
        self.id = str(uuid.uuid4())
        self.token = assinar(
            conteudo_valido(aud=DESTINATARIO_DO_MCP, sub=self.id, perfil="vendas"), CHAVE
        )


@pytest.fixture
def relogio() -> RelogioFalso:
    return RelogioFalso()


@pytest.fixture
def mcp_com_limite(criar_mcp, relogio):
    """A aplicação do servidor MCP com o limite de chamadas dado, por janela de 60 segundos."""

    def criar(chamadas: int):
        limite = LimiteDeFrequencia(chamadas=chamadas, janela_em_segundos=JANELA, relogio=relogio)
        return criar_mcp(chaves=ChavesLocais(CHAVE), limite=limite)

    return criar


def test_a_chamada_alem_do_limite_e_barrada_e_registrada_como_limitada(mcp_com_limite):
    mcp = mcp_com_limite(2)
    ana = Usuario()

    for _ in range(2):
        assert not chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"}).is_error
    barrada = chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})

    assert texto_do_erro(barrada) == LIMITADA
    linha = ultima_chamada_de(ana.id)
    assert linha["resultado"] == "limitada"
    assert linha["ferramenta"] == FERRAMENTA
    assert linha["parametros"] == {"periodo": "30d"}


def test_o_limite_de_um_usuario_nao_afeta_outro_do_mesmo_perfil(mcp_com_limite):
    mcp = mcp_com_limite(1)
    ana, outra = Usuario(), Usuario()
    chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})
    assert chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"}).is_error

    resultado = chamar(mcp, outra.token, FERRAMENTA, {"periodo": "30d"})

    assert not resultado.is_error
    assert ultima_chamada_de(outra.id)["resultado"] == "permitida"


def test_chamadas_negadas_e_com_parametro_invalido_contam_para_o_limite(mcp_com_limite):
    mcp = mcp_com_limite(2)
    ana = Usuario()
    assert chamar(mcp, ana.token, "vendas_margem_por_cliente").is_error
    assert chamar(mcp, ana.token, FERRAMENTA, {"periodo": "um século"}).is_error

    resultado = chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})

    assert texto_do_erro(resultado) == LIMITADA


def test_a_chamada_barrada_nao_conta_para_o_limite(mcp_com_limite, relogio):
    mcp = mcp_com_limite(2)
    ana = Usuario()
    chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})
    relogio.avancar(30)
    chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})
    relogio.avancar(10)
    assert texto_do_erro(chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})) == LIMITADA

    # Só a primeira chamada saiu da janela. Se a barrada contasse, ainda não haveria vaga.
    relogio.avancar(21)
    resultado = chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})

    assert not resultado.is_error


def test_listar_ferramentas_nao_conta_para_o_limite(mcp_com_limite):
    mcp = mcp_com_limite(1)
    ana = Usuario()
    for _ in range(3):
        assert listar_ferramentas(mcp, ana.token)

    resultado = chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})

    assert not resultado.is_error


def test_o_usuario_volta_a_chamar_quando_a_janela_passa(mcp_com_limite, relogio):
    mcp = mcp_com_limite(1)
    ana = Usuario()
    chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})
    assert texto_do_erro(chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})) == LIMITADA

    relogio.avancar(JANELA)
    resultado = chamar(mcp, ana.token, FERRAMENTA, {"periodo": "30d"})

    assert not resultado.is_error
    assert ultima_chamada_de(ana.id)["resultado"] == "permitida"


def chamadas_admitidas(limite: LimiteDeFrequencia, usuario: str, tentativas: int) -> int:
    return sum(limite.admitir(usuario) for _ in range(tentativas))


def test_sem_variaveis_de_ambiente_o_limite_e_30_chamadas_por_60_segundos(relogio):
    limite = limite_do_ambiente({}, relogio=relogio)

    assert chamadas_admitidas(limite, "ana", 40) == 30
    relogio.avancar(59)
    assert chamadas_admitidas(limite, "ana", 1) == 0
    relogio.avancar(1)
    assert chamadas_admitidas(limite, "ana", 40) == 30


def test_o_limite_e_a_janela_vem_das_variaveis_de_ambiente(relogio):
    ambiente = {"LIMITE_DE_CHAMADAS_POR_USUARIO": "5", "JANELA_DO_LIMITE_EM_SEGUNDOS": "10"}
    limite = limite_do_ambiente(ambiente, relogio=relogio)

    assert chamadas_admitidas(limite, "ana", 8) == 5
    relogio.avancar(10)
    assert chamadas_admitidas(limite, "ana", 8) == 5
