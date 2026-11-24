"""A gravação de uma chamada na auditoria, uma linha por chamada, com o desfecho final."""

import os
from datetime import datetime
from enum import StrEnum
from types import TracebackType
from typing import Any, Protocol

import psycopg
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout

from acesso import UsuarioAutenticado
from consultas import BancoDeDados, Credencial

BANCO = "auditoria"
PAPEL = "auditoria"
# Quanto uma chamada espera pela auditoria antes de desistir.
ESPERA_POR_CONEXAO_EM_SEGUNDOS = 5
CONEXOES = 4

# Sem `returning`: exigiria `select`, que o papel não tem (RF-32).
GRAVACAO = """
insert into auditoria.chamada (
    horario, id_do_usuario, nome_do_usuario, perfil, ferramenta, parametros,
    parametros_cortados, resultado
) values (%s, %s, %s, %s, %s, %s, %s, %s)
"""


class Resultado(StrEnum):
    PERMITIDA = "permitida"
    NEGADA = "negada"
    PARAMETRO_INVALIDO = "parametro_invalido"
    LIMITADA = "limitada"
    FALHA = "falha"


class AuditoriaIndisponivel(Exception):
    """A chamada não pôde ser gravada. O motivo é só para o log; a chamada é recusada."""


class Auditoria(Protocol):
    """Onde o servidor MCP registra cada chamada."""

    def registrar(
        self,
        usuario: UsuarioAutenticado,
        ferramenta: str,
        argumentos: dict[str, Any],
        resultado: Resultado,
        horario: datetime,
    ) -> None:
        """Grava a chamada ou levanta AuditoriaIndisponivel."""


class AuditoriaNoBanco:
    """A auditoria no banco próprio, com um pool de conexões do papel `auditoria`.

    Feche ao terminar (`with` ou `fechar()`).
    """

    def __init__(self, banco: BancoDeDados, credencial: Credencial) -> None:
        self._pool = ConnectionPool(
            kwargs={
                "host": banco.host,
                "port": banco.porta,
                "dbname": banco.nome,
                "user": credencial.papel,
                "password": credencial.senha,
                "connect_timeout": ESPERA_POR_CONEXAO_EM_SEGUNDOS,
                "autocommit": True,
            },
            # Sem conexão aberta na subida: o servidor sobe mesmo com a auditoria fora, e é a
            # chamada que é recusada.
            min_size=0,
            max_size=CONEXOES,
            timeout=ESPERA_POR_CONEXAO_EM_SEGUNDOS,
            check=ConnectionPool.check_connection,
            name="auditoria",
            open=True,
        )

    def registrar(
        self,
        usuario: UsuarioAutenticado,
        ferramenta: str,
        argumentos: dict[str, Any],
        resultado: Resultado,
        horario: datetime,
    ) -> None:
        try:
            with self._pool.connection() as conexao:
                conexao.execute(
                    GRAVACAO,
                    (
                        horario,
                        usuario.id,
                        usuario.nome,
                        usuario.perfil.value,
                        ferramenta,
                        Jsonb(argumentos),
                        False,
                        resultado.value,
                    ),
                )
        except (psycopg.Error, PoolTimeout) as erro:
            raise AuditoriaIndisponivel(str(erro)) from erro

    def fechar(self) -> None:
        self._pool.close()

    def __enter__(self) -> "AuditoriaNoBanco":
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        erro: BaseException | None,
        rastro: TracebackType | None,
    ) -> None:
        self.fechar()


def auditoria_do_ambiente() -> AuditoriaNoBanco:
    """A auditoria no Postgres do ambiente, pela rede interna do compose."""
    banco = BancoDeDados(
        host=os.environ["POSTGRES_HOST"],
        porta=int(os.environ.get("POSTGRES_INTERNAL_PORT", "5432")),
        nome=BANCO,
    )
    return AuditoriaNoBanco(banco, Credencial(PAPEL, os.environ["SENHA_DO_PAPEL_AUDITORIA"]))
