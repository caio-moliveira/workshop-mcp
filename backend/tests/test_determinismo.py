"""Duas cargas com a mesma configuração produzem o mesmo banco, em qualquer dia."""

from datetime import date

import pytest
from apoio import (
    conectar_como_dono,
    impressao_digital_atual,
    intervalo_de_datas,
    rodar_carga,
    tabelas_dos_dados_de_origem,
)


@pytest.fixture
def recarga_ao_final():
    """Testes que carregam outra configuração devolvem o banco à carga padrão."""
    yield
    rodar_carga()


def test_duas_cargas_seguidas_tem_a_mesma_impressao_digital():
    primeira = rodar_carga()
    segunda = rodar_carga()

    assert primeira
    assert primeira == segunda


def test_impressao_digital_cobre_todas_as_tabelas_dos_dados_de_origem():
    impressao = rodar_carga()
    # A carga recria o banco e derruba conexões abertas antes dela.
    with conectar_como_dono() as conexao:
        tabelas = tabelas_dos_dados_de_origem(conexao)

    assert set(impressao) == tabelas


def test_outra_semente_muda_a_impressao_digital(recarga_ao_final):
    padrao = rodar_carga()
    outra = rodar_carga("SEMENTE=7")

    assert all(outra[tabela] != padrao[tabela] for tabela in ("lead", "lojista", "produto"))


def test_dados_terminam_na_data_de_referencia_configurada():
    rodar_carga()
    with conectar_como_dono() as conexao:
        menor, maior = intervalo_de_datas(conexao)

    # Valor inicial da data de referência no PRD de dados.
    assert maior <= date(2026, 11, 30)
    assert maior >= date(2026, 11, 1)
    assert menor >= date(2024, 9, 1)


def test_mudar_a_data_de_referencia_desloca_todas_as_datas(recarga_ao_final):
    rodar_carga("DATA_REFERENCIA=2025-11-30")
    with conectar_como_dono() as conexao:
        menor, maior = intervalo_de_datas(conexao)
        antes_da_janela = conexao.execute(
            "select count(*) from dados_de_origem.lead"
            " where etapa = 'Fechado' and data_fechamento < date '2023-12-01'"
        ).fetchone()[0]

    assert date(2025, 11, 1) <= maior <= date(2025, 11, 30)
    assert menor >= date(2023, 9, 1)
    assert 72 <= antes_da_janela <= 88


def test_recarga_devolve_o_banco_alterado_ao_estado_inicial(recarga_ao_final):
    inicial = rodar_carga()
    assert impressao_digital_atual() == inicial

    with conectar_como_dono() as conexao:
        conexao.execute("delete from dados_de_origem.avaliacao where nota = 1")
        conexao.execute("update dados_de_origem.pedido set valor_frete = 0 where id <= 100")
    alterada = impressao_digital_atual()
    assert alterada["avaliacao"] != inicial["avaliacao"]
    assert alterada["pedido"] != inicial["pedido"]

    assert rodar_carga() == inicial
