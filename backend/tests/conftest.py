"""Fixtures da costura de teste da entrega 1: o banco carregado."""

from collections.abc import Iterator

import psycopg
import pytest
from apoio import conectar_como_dono


@pytest.fixture
def conexao_dono() -> Iterator[psycopg.Connection]:
    """Conexão com o banco carregado usando o papel dono."""
    with conectar_como_dono() as conexao:
        yield conexao
