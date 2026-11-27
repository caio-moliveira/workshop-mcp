"""A auditoria: o registro permanente de toda chamada ao servidor MCP (RF-30, ADR 0008).

Grava no banco próprio da auditoria, com o papel `auditoria`, que só pode inserir. Só a API lê
as últimas chamadas, para o painel de segurança, com o papel `leitura_da_auditoria` (ADR 0012).
"""

from auditoria.leitura import (
    CHAMADAS_AO_VIVO,
    PAPEL_DE_LEITURA,
    VARIAVEL_DA_SENHA_DE_LEITURA,
    ChamadaLida,
    LeituraDaAuditoria,
    LeituraDaAuditoriaNoBanco,
    leitura_da_auditoria_do_ambiente,
)
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
    "CHAMADAS_AO_VIVO",
    "PAPEL",
    "PAPEL_DE_LEITURA",
    "VARIAVEL_DA_SENHA_DE_LEITURA",
    "Auditoria",
    "AuditoriaIndisponivel",
    "AuditoriaNoBanco",
    "Chamada",
    "ChamadaLida",
    "LeituraDaAuditoria",
    "LeituraDaAuditoriaNoBanco",
    "Resultado",
    "auditoria_do_ambiente",
    "leitura_da_auditoria_do_ambiente",
]
