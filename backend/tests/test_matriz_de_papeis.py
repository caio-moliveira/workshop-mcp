"""A matriz de papéis: cada papel de perfil contra cada camada de leitura e os dados de origem.

Os papéis e as camadas são lidos do banco: os papéis de perfil que existem no servidor e os
esquemas com o nome de um perfil. Cada papel lê toda view da própria camada e é recusado em toda
view das outras e em toda tabela dos dados de origem (ADR 0002, RS-04). Um papel ou uma camada
nova entra na matriz sem mudar este teste.
"""

import psycopg
from apoio import (
    camadas_de_leitura,
    conectar_como_perfil,
    papeis_de_perfil,
    tabelas_dos_dados_de_origem,
)

from acesso import Perfil

LE = "lê"
VAZIA = "lê, mas vazia"
RECUSADO = "recusado"


def _acesso(conexao: psycopg.Connection, tabela: str) -> str:
    """O que o papel da conexão consegue na tabela: ler linhas, ler nada ou ser recusado."""
    try:
        linhas = conexao.execute(f"select count(*) from {tabela}").fetchone()[0]
    except psycopg.errors.InsufficientPrivilege:
        return RECUSADO
    return LE if linhas else VAZIA


def test_todo_papel_de_perfil_tem_a_propria_camada_de_leitura(conexao_dono):
    papeis = papeis_de_perfil(conexao_dono)

    assert Perfil.VENDAS in papeis
    assert set(camadas_de_leitura(conexao_dono)) == set(papeis)


def test_cada_papel_le_so_a_propria_camada_e_nada_dos_dados_de_origem(conexao_dono):
    camadas = camadas_de_leitura(conexao_dono)
    origem = sorted(tabelas_dos_dados_de_origem(conexao_dono))
    assert camadas
    assert origem

    esperado, obtido = {}, {}
    for papel in papeis_de_perfil(conexao_dono):
        with conectar_como_perfil(papel) as conexao:
            for camada, views in camadas.items():
                for view in views:
                    chave = (papel.value, f"{camada}.{view}")
                    esperado[chave] = LE if camada is papel else RECUSADO
                    obtido[chave] = _acesso(conexao, f"{camada}.{view}")
            for tabela in origem:
                chave = (papel.value, f"dados_de_origem.{tabela}")
                esperado[chave] = RECUSADO
                obtido[chave] = _acesso(conexao, f"dados_de_origem.{tabela}")

    assert obtido == esperado
