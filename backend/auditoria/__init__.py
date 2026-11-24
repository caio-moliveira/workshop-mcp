"""A auditoria: o registro permanente de toda chamada ao servidor MCP (RF-30, ADR 0008).

Grava no banco próprio da auditoria, com o papel `auditoria`, que só pode inserir.
"""

from auditoria.registro import (
    Auditoria,
    AuditoriaIndisponivel,
    AuditoriaNoBanco,
    Resultado,
    auditoria_do_ambiente,
)

__all__ = [
    "Auditoria",
    "AuditoriaIndisponivel",
    "AuditoriaNoBanco",
    "Resultado",
    "auditoria_do_ambiente",
]
