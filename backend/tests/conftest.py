"""Fixtures das costuras de teste: o banco carregado (entrega 1) e a API por HTTP (entrega 2)."""

from collections.abc import Callable, Iterator
from dataclasses import replace

import psycopg
import pytest
from apoio import conectar_como_dono, variavel
from fastapi.testclient import TestClient
from provedor import DESTINATARIO_DA_API, emissor, url_das_chaves

from acesso import ChavesDoProvedor, ConfiguracaoDeAcesso
from api import criar_aplicacao


@pytest.fixture
def conexao_dono() -> Iterator[psycopg.Connection]:
    """Conexão com o banco carregado usando o papel dono."""
    with conectar_como_dono() as conexao:
        yield conexao


@pytest.fixture
def criar_cliente_da_api() -> Callable[..., TestClient]:
    """Cria a API pela fábrica, dentro do processo, validando tokens do provedor real.

    Cada parâmetro da configuração de acesso pode ser trocado: o relógio, as chaves, o emissor.
    A origem do frontend liberada pelo CORS é a do ambiente.
    """

    def criar(**sobreposicoes) -> TestClient:
        configuracao = ConfiguracaoDeAcesso(
            emissor=emissor(),
            destinatario=DESTINATARIO_DA_API,
            chaves=ChavesDoProvedor(url_das_chaves()),
        )
        aplicacao = criar_aplicacao(
            replace(configuracao, **sobreposicoes),
            origem_do_frontend=variavel("ENDERECO_DO_FRONTEND"),
        )
        return TestClient(aplicacao)

    return criar


@pytest.fixture
def cliente_da_api(criar_cliente_da_api) -> TestClient:
    """A API com a configuração de produção, apontada para o provedor real."""
    return criar_cliente_da_api()
