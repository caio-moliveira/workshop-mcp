"""O executor: confere o perfil, escolhe o papel e roda a consulta numa conexão do pool dele."""

import logging
import os
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from types import TracebackType

import psycopg
from psycopg_pool import ConnectionPool, PoolTimeout

from acesso import Perfil, UsuarioAutenticado
from consultas import pergunta_no_log
from consultas.registro import Consulta

registro = logging.getLogger("consultas")

# Uma consulta lenta falha em vez de prender a conexão (RNF-05).
LIMITE_POR_CONSULTA_EM_MILISSEGUNDOS = 3000
# Quanto um pedido espera por uma conexão livre do pool antes de desistir.
ESPERA_POR_CONEXAO_EM_SEGUNDOS = 5
CONEXOES_POR_PAPEL = 4


class AcessoNegado(Exception):
    """O usuário não pode executar a consulta. O motivo é só para o log (RF-11)."""


class ConsultaFalhou(Exception):
    """O banco não respondeu ou recusou a consulta. O motivo real é só para o log."""


@dataclass(frozen=True)
class BancoDeDados:
    host: str
    porta: int
    nome: str


@dataclass(frozen=True)
class Credencial:
    """O usuário e a senha com que um serviço conecta ao banco usando um papel."""

    papel: str
    senha: str

    def __repr__(self) -> str:
        return f"Credencial(papel={self.papel!r})"


def banco_do_ambiente() -> BancoDeDados:
    """O banco carregado, pela rede interna do compose."""
    return BancoDeDados(
        host=os.environ["POSTGRES_HOST"],
        porta=int(os.environ.get("POSTGRES_INTERNAL_PORT", "5432")),
        nome=os.environ["BANCO"],
    )


def credenciais_do_ambiente() -> dict[Perfil, Credencial]:
    """A credencial de cada perfil cujo papel tem senha no ambiente (SENHA_DO_PAPEL_<PERFIL>).

    O papel de um perfil tem o nome do perfil, como a carga o cria. Perfil sem senha configurada
    fica sem credencial, e toda consulta dele é negada.
    """
    credenciais = {}
    for perfil in Perfil:
        senha = os.environ.get(f"SENHA_DO_PAPEL_{perfil.name}")
        if senha:
            credenciais[perfil] = Credencial(papel=perfil.value, senha=senha)
    return credenciais


class ExecutorDeConsultas:
    """Executa consultas em nome de usuários autenticados, com um pool de conexões por papel.

    Os pools nascem no primeiro uso de cada papel. Feche o executor ao terminar (`with` ou
    `fechar()`).
    """

    def __init__(self, banco: BancoDeDados, credenciais: Mapping[Perfil, Credencial]) -> None:
        self._banco = banco
        self._credenciais = dict(credenciais)
        self._pools: dict[Perfil, ConnectionPool] = {}
        self._trava = threading.Lock()

    def autorizar(self, usuario: UsuarioAutenticado, consulta: Consulta) -> None:
        """Nega, sem conectar, o perfil diferente do da consulta e o perfil sem credencial."""
        if usuario.perfil is not consulta.perfil:
            raise AcessoNegado(f"perfil {usuario.perfil} pediu a consulta {consulta.nome}")
        if consulta.perfil not in self._credenciais:
            raise AcessoNegado(f"perfil {consulta.perfil} sem credencial configurada")

    def executar[R](self, usuario: UsuarioAutenticado, consulta: Consulta[R], **parametros) -> R:
        """Roda a consulta com o papel do perfil. Os parâmetros já chegam validados.

        Toda consulta executada deixa uma linha no log, com o nome, a duração e a pergunta do
        assistente que a pediu, quando veio de uma (RNF-06). Sem os parâmetros nem o resultado.
        """
        self.autorizar(usuario, consulta)
        inicio = time.monotonic()
        try:
            with self._pool_de(consulta.perfil).connection() as conexao:
                return consulta.ler(conexao, **parametros)
        except (psycopg.Error, PoolTimeout) as erro:
            raise ConsultaFalhou(f"{consulta.nome}: {erro}") from erro
        finally:
            registro.info(
                "consulta %s executada: %d ms, %s",
                consulta.nome,
                round((time.monotonic() - inicio) * 1000),
                pergunta_no_log.atual(),
            )

    def fechar(self) -> None:
        with self._trava:
            for pool in self._pools.values():
                pool.close()
            self._pools.clear()

    def __enter__(self) -> "ExecutorDeConsultas":
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        erro: BaseException | None,
        rastro: TracebackType | None,
    ) -> None:
        self.fechar()

    def _pool_de(self, perfil: Perfil) -> ConnectionPool:
        with self._trava:
            if perfil not in self._pools:
                self._pools[perfil] = self._abrir_pool(self._credenciais[perfil])
            return self._pools[perfil]

    def _abrir_pool(self, credencial: Credencial) -> ConnectionPool:
        registro.info("abrindo o pool de conexões do papel %s", credencial.papel)
        return ConnectionPool(
            kwargs={
                "host": self._banco.host,
                "port": self._banco.porta,
                "dbname": self._banco.nome,
                "user": credencial.papel,
                "password": credencial.senha,
                "connect_timeout": ESPERA_POR_CONEXAO_EM_SEGUNDOS,
                "options": f"-c statement_timeout={LIMITE_POR_CONSULTA_EM_MILISSEGUNDOS}",
                "autocommit": True,
            },
            min_size=1,
            max_size=CONEXOES_POR_PAPEL,
            timeout=ESPERA_POR_CONEXAO_EM_SEGUNDOS,
            # A recarga derruba as conexões abertas: confere cada uma antes de entregá-la.
            check=ConnectionPool.check_connection,
            name=f"papel-{credencial.papel}",
            open=True,
        )
