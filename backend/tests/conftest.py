"""Fixtures das costuras de teste: o banco carregado (entrega 1) e a API por HTTP (entrega 2).

Desde a entrega 3, a API também lê o banco, pelo mecanismo de consultas, com o papel de cada perfil.
"""

import time
from collections.abc import Callable, Iterator
from dataclasses import replace

import psycopg
import pytest
from apoio import banco_local, conectar_como_dono, variavel
from fastapi.testclient import TestClient
from provedor import (
    DESTINATARIO_DA_API,
    USUARIOS_DE_DEMONSTRACAO,
    emissor,
    token_pelo_fluxo_de_codigo,
    url_das_chaves,
)

from acesso import ChavesDoProvedor, ConfiguracaoDeAcesso, Perfil
from api import criar_aplicacao
from consultas import ExecutorDeConsultas, credenciais_do_ambiente

# O token de acesso vale 5 minutos; um token guardado é trocado bem antes de vencer.
VALIDADE_DO_TOKEN_GUARDADO_EM_SEGUNDOS = 3 * 60


@pytest.fixture
def conexao_dono() -> Iterator[psycopg.Connection]:
    """Conexão com o banco carregado usando o papel dono."""
    with conectar_como_dono() as conexao:
        yield conexao


@pytest.fixture(scope="session")
def executor_de_consultas() -> Iterator[ExecutorDeConsultas]:
    """O executor de consultas com as credenciais do ambiente, apontado para o banco local."""
    with ExecutorDeConsultas(banco_local(), credenciais_do_ambiente()) as executor:
        yield executor


@pytest.fixture
def criar_api(executor_de_consultas) -> Callable[..., TestClient]:
    """Cria a API pela fábrica, dentro do processo, validando tokens do provedor real.

    Cada parâmetro da configuração de acesso pode ser trocado: o relógio, as chaves, o emissor.
    O executor de consultas também, com `consultas=`. A origem do frontend liberada pelo CORS é a
    do ambiente.
    """

    def criar(consultas: ExecutorDeConsultas | None = None, **sobreposicoes) -> TestClient:
        configuracao = ConfiguracaoDeAcesso(
            emissor=emissor(),
            destinatario=DESTINATARIO_DA_API,
            chaves=ChavesDoProvedor(url_das_chaves()),
        )
        aplicacao = criar_aplicacao(
            replace(configuracao, **sobreposicoes),
            origem_do_frontend=variavel("ENDERECO_DO_FRONTEND"),
            consultas=consultas or executor_de_consultas,
        )
        return TestClient(aplicacao)

    return criar


@pytest.fixture
def api(criar_api) -> TestClient:
    """A API com a configuração de produção, apontada para o provedor real."""
    return criar_api()


@pytest.fixture(scope="session")
def token_de() -> Callable[[Perfil], str]:
    """O token de acesso do usuário de demonstração de um perfil, pelo fluxo de código.

    Guardado entre testes para não refazer o login a cada pedido, e trocado antes de vencer.
    """
    guardados: dict[Perfil, tuple[str, float]] = {}

    def token(perfil: Perfil) -> str:
        guardado = guardados.get(perfil)
        if guardado and time.monotonic() - guardado[1] < VALIDADE_DO_TOKEN_GUARDADO_EM_SEGUNDOS:
            return guardado[0]
        demonstracao = next(u for u in USUARIOS_DE_DEMONSTRACAO if u.perfil == perfil)
        novo = token_pelo_fluxo_de_codigo(demonstracao.nome_de_usuario, demonstracao.senha())
        guardados[perfil] = (novo, time.monotonic())
        return novo

    return token
