"""A leitura das últimas chamadas da auditoria, para as chamadas ao vivo do painel de segurança.

Só a API lê, e só com o interruptor de demonstração ligado, com o papel `leitura_da_auditoria`,
que só tem `select` na tabela (ADR 0012). O servidor MCP continua só gravando, e nenhuma
ferramenta alcança a auditoria (RF-32).
"""

import os
from dataclasses import dataclass, replace
from datetime import datetime
from types import TracebackType
from typing import Protocol

import psycopg
from psycopg_pool import PoolTimeout

from auditoria.registro import BANCO, AuditoriaIndisponivel, Resultado, pool_da_auditoria
from consultas import BancoDeDados, Credencial, banco_do_ambiente

# O papel que só lê a auditoria. A carga o cria com este nome.
PAPEL_DE_LEITURA = "leitura_da_auditoria"
VARIAVEL_DA_SENHA_DE_LEITURA = "SENHA_DO_PAPEL_LEITURA_DA_AUDITORIA"
# Quantas chamadas o painel mostra: as mais recentes.
CHAMADAS_AO_VIVO = 20

# Sem o `sub` nem os parâmetros: quem pediu, pelo nome, e o que pediu bastam para o painel, e um
# parâmetro pode trazer texto qualquer de quem chamou.
LEITURA = """
select horario, nome_do_usuario, perfil, ferramenta, resultado
from auditoria.chamada
order by id desc
limit %s
"""


@dataclass(frozen=True)
class ChamadaLida:
    """Uma chamada lida da auditoria, como o painel a mostra."""

    horario: datetime
    usuario: str
    perfil: str
    ferramenta: str
    resultado: Resultado


class LeituraDaAuditoria(Protocol):
    """De onde a API lê as últimas chamadas ao servidor MCP."""

    def ultimas_chamadas(self) -> list[ChamadaLida]:
        """As chamadas mais recentes, da última para a primeira, ou AuditoriaIndisponivel."""


class LeituraDaAuditoriaNoBanco:
    """A leitura no banco da auditoria, com um pool do papel `leitura_da_auditoria`.

    Feche ao terminar (`with` ou `fechar()`).
    """

    def __init__(
        self, banco: BancoDeDados, credencial: Credencial, chamadas: int = CHAMADAS_AO_VIVO
    ) -> None:
        self._chamadas = chamadas
        self._pool = pool_da_auditoria(banco, credencial, "leitura_da_auditoria")

    def ultimas_chamadas(self) -> list[ChamadaLida]:
        try:
            with self._pool.connection() as conexao:
                linhas = conexao.execute(LEITURA, (self._chamadas,)).fetchall()
        except (psycopg.Error, PoolTimeout) as erro:
            raise AuditoriaIndisponivel(str(erro)) from erro
        return [
            ChamadaLida(
                horario=horario,
                usuario=usuario,
                perfil=perfil,
                ferramenta=ferramenta,
                resultado=Resultado(resultado),
            )
            for horario, usuario, perfil, ferramenta, resultado in linhas
        ]

    def fechar(self) -> None:
        self._pool.close()

    def __enter__(self) -> "LeituraDaAuditoriaNoBanco":
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        erro: BaseException | None,
        rastro: TracebackType | None,
    ) -> None:
        self.fechar()


def leitura_da_auditoria_do_ambiente() -> LeituraDaAuditoriaNoBanco:
    """A leitura da auditoria no Postgres do ambiente, o mesmo servidor do banco carregado."""
    banco = replace(banco_do_ambiente(), nome=BANCO)
    senha = os.environ[VARIAVEL_DA_SENHA_DE_LEITURA]
    return LeituraDaAuditoriaNoBanco(banco, Credencial(PAPEL_DE_LEITURA, senha))
