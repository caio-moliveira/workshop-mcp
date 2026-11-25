"""Negar é o padrão: toda rota da API declara um perfil ou está na lista de rotas só autenticadas.

Uma rota nova que não sirva uma consulta (com o perfil que ela declara) nem esteja na lista
explícita faz este teste falhar antes de ser publicada (RS-05).
"""

import pytest
from fastapi.routing import APIRoute

from acesso import Perfil
from api.aplicacao import ROTAS_SO_AUTENTICADAS, RotaDeConsulta
from consultas import consulta

# A lista explícita, repetida aqui de propósito: aumentá-la exige mudar também este teste.
# O assistente não tem regra de perfil própria: o que ele alcança é o que o servidor MCP lista e
# permite para o token do usuário (RF-13). O histórico também não: cada usuário só alcança as
# próprias conversas, de qualquer perfil (RF-18).
ROTAS_QUE_SO_EXIGEM_AUTENTICACAO = {"/eu", "/assistente", "/conversas/{id_da_conversa}"}


def test_a_lista_de_rotas_so_autenticadas_e_a_esperada():
    assert ROTAS_SO_AUTENTICADAS == ROTAS_QUE_SO_EXIGEM_AUTENTICACAO


def test_toda_rota_declara_perfil_ou_esta_na_lista_de_rotas_so_autenticadas(api):
    rotas = [rota for rota in api.app.routes if isinstance(rota, APIRoute)]
    assert rotas

    sem_perfil = [
        rota.path
        for rota in rotas
        if not (isinstance(rota, RotaDeConsulta) and isinstance(rota.consulta.perfil, Perfil))
        and rota.path not in ROTAS_QUE_SO_EXIGEM_AUTENTICACAO
    ]

    assert sem_perfil == []


def test_toda_rota_de_dados_so_aceita_get(api):
    for rota in api.app.routes:
        if isinstance(rota, RotaDeConsulta):
            assert rota.methods == {"GET"}, rota.path


def test_uma_consulta_sem_perfil_nao_pode_ser_registrada():
    with pytest.raises(TypeError):

        @consulta("vendas")
        def sem_perfil_tipado(conexao, periodo): ...

    with pytest.raises(TypeError):

        @consulta(None)
        def sem_perfil(conexao, periodo): ...
