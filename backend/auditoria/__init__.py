"""A auditoria: o registro permanente de toda chamada ao servidor MCP (RF-30, ADR 0008).

Grava no banco próprio da auditoria, com o papel `auditoria`, que só pode inserir.
"""

from auditoria.registro import (
    BANCO,
    PAPEL,
    Auditoria,
    AuditoriaIndisponivel,
    AuditoriaNoBanco,
    Chamada,
    Resultado,
    auditoria_do_ambiente,
)

__all__ = [
    "BANCO",
    "PAPEL",
    "Auditoria",
    "AuditoriaIndisponivel",
    "AuditoriaNoBanco",
    "Chamada",
    "Resultado",
    "auditoria_do_ambiente",
]
