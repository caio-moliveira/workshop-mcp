"""O identificador da pergunta nos logs: o que liga a pergunta, na API, às chamadas no servidor MCP
e às consultas executadas (RNF-06).

A API gera o identificador e o envia ao servidor MCP no cabeçalho abaixo. Quem o recebe o guarda
no contexto da requisição, e o executor de consultas o põe na linha de cada consulta. Fica aqui,
no mecanismo de consultas, por ser o único pacote que a API e o servidor MCP compartilham e que
escreve a última das três linhas. A auditoria não o recebe (fora do escopo da 5b).
"""

import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

CABECALHO = "Id-Da-Pergunta"
# Só o formato canônico, 8-4-4-4-12 em hexadecimal: o valor vem de fora e vai para o log.
_FORMATO = re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}")
# Como a linha diz que a chamada ou a consulta não veio de uma pergunta do assistente.
SEM_PERGUNTA = "sem pergunta"

_atual: ContextVar[uuid.UUID | None] = ContextVar("id_da_pergunta", default=None)


def ler(valor: str | None) -> uuid.UUID | None:
    """O identificador do cabeçalho, ou nada quando falta ou está fora do formato de UUID."""
    if valor is None or not _FORMATO.fullmatch(valor):
        return None
    return uuid.UUID(valor)


@contextmanager
def pergunta(identificador: uuid.UUID | None) -> Iterator[None]:
    """Dentro do bloco, o que for feito pertence à pergunta dada (ou a nenhuma)."""
    marca = _atual.set(identificador)
    try:
        yield
    finally:
        _atual.reset(marca)


def no_log() -> str:
    """A pergunta em curso como vai para o log."""
    identificador = _atual.get()
    return f"pergunta {identificador}" if identificador else SEM_PERGUNTA
