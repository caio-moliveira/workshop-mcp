"""As chamadas ao vivo do painel de segurança: as últimas chamadas ao servidor MCP, da auditoria.

A rota só existe com o interruptor de demonstração ligado, como o painel (ADR 0012). Qualquer
perfil autenticado a lê, e sem token ela recusa (RS-05). Ela traz quem chamou, pelo nome, o
perfil, a ferramenta e o desfecho; nem o `sub` do usuário nem os parâmetros saem por ela.
"""

import uuid
from datetime import UTC, datetime

import pytest
from recusa import assert_recusado, pedir
from registros import DONO_DA_ROTA

from acesso import Perfil, UsuarioAutenticado
from api.aplicacao import INDISPONIVEL
from auditoria import CHAMADAS_AO_VIVO, AuditoriaIndisponivel, Chamada, ChamadaLida, Resultado

ROTA = "/seguranca/chamadas"


class AuditoriaFora:
    """A leitura da auditoria com o banco fora do ar."""

    def ultimas_chamadas(self) -> list[ChamadaLida]:
        raise AuditoriaIndisponivel("banco da auditoria fora do ar")


@pytest.fixture
def api_ligada(criar_api, tmp_path, leitura_da_auditoria_local):
    return criar_api(execucao_de_aceite=tmp_path, leitura_da_auditoria=leitura_da_auditoria_local)


def _registrar(auditoria_local, resultado: Resultado = Resultado.NEGADA) -> tuple[str, str]:
    """Grava uma chamada como o servidor MCP grava e devolve o `sub` e o nome dela, únicos."""
    sub = f"teste-ao-vivo-{uuid.uuid4()}"
    nome = f"teste.{uuid.uuid4().hex[:8]}"
    auditoria_local.registrar(
        Chamada(
            usuario=UsuarioAutenticado(id=sub, nome=nome, perfil=Perfil.VENDAS),
            ferramenta="diretoria_indicadores",
            argumentos={"periodo": "texto-plantado-nos-parametros"},
            resultado=resultado,
            horario=datetime.now(UTC),
        )
    )
    return sub, nome


@pytest.mark.parametrize("perfil", list(Perfil), ids=str)
def test_os_quatro_perfis_veem_a_chamada_mais_recente_primeiro(
    api_ligada, auditoria_local, token_de, perfil
):
    _, nome = _registrar(auditoria_local)

    resposta = pedir(api_ligada, ROTA, token_de(perfil))

    assert resposta.status_code == 200
    primeira = resposta.json()["chamadas"][0]
    assert primeira["usuario"] == nome
    assert primeira["perfil"] == "vendas"
    assert primeira["ferramenta"] == "diretoria_indicadores"
    assert primeira["resultado"] == "negada"
    datetime.fromisoformat(primeira["horario"])


def test_so_o_que_o_painel_mostra_sai_pela_rota(api_ligada, auditoria_local, token_de):
    sub, _ = _registrar(auditoria_local)

    resposta = pedir(api_ligada, ROTA, token_de(Perfil.DIRETORIA))

    primeira = resposta.json()["chamadas"][0]
    assert set(primeira) == {"horario", "usuario", "perfil", "ferramenta", "resultado"}
    assert sub not in resposta.text
    assert "texto-plantado-nos-parametros" not in resposta.text


def test_traz_no_maximo_as_ultimas_chamadas_do_painel(api_ligada, auditoria_local, token_de):
    for _ in range(CHAMADAS_AO_VIVO + 1):
        _registrar(auditoria_local, Resultado.PERMITIDA)

    chamadas = pedir(api_ligada, ROTA, token_de(Perfil.COMERCIAL)).json()["chamadas"]

    assert len(chamadas) == CHAMADAS_AO_VIVO
    horarios = [datetime.fromisoformat(c["horario"]) for c in chamadas]
    assert horarios == sorted(horarios, reverse=True)


def test_sem_token_a_rota_recusa(api_ligada):
    assert_recusado(pedir(api_ligada, ROTA))


def test_com_a_auditoria_fora_do_ar_a_rota_responde_indisponivel(criar_api, tmp_path, token_de):
    api = criar_api(execucao_de_aceite=tmp_path, leitura_da_auditoria=AuditoriaFora())

    resposta = pedir(api, ROTA, token_de(Perfil.PRODUTOS))

    assert resposta.status_code == 503
    assert resposta.json() == INDISPONIVEL
    assert "banco da auditoria" not in resposta.text


def test_desligado_a_rota_responde_como_uma_rota_inexistente(
    criar_api, leitura_da_auditoria_local, token_de
):
    # Mesmo com a leitura dada: sem o interruptor, não há painel nem chamadas ao vivo.
    api = criar_api(leitura_da_auditoria=leitura_da_auditoria_local)
    token = token_de(Perfil.VENDAS)

    chamadas = pedir(api, ROTA, token)
    inexistente = pedir(api, "/rota-que-nunca-existiu", token)

    assert chamadas.status_code == inexistente.status_code == 404
    assert chamadas.content == inexistente.content
    assert pedir(api, ROTA).status_code == 404


def test_a_rota_nao_entra_no_registro_das_rotas_de_dados(api_ligada):
    """Sem dono, como o painel: fica fora da matriz de isolamento."""
    assert ROTA not in DONO_DA_ROTA
    assert ROTA in {rota.path for rota in api_ligada.app.routes}
