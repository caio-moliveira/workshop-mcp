"""O histórico: as conversas gravadas de cada usuário com o assistente (RF-18, ADR 0009).

Vive num banco próprio, lido e gravado só pela API, com o papel `historico`. Toda operação recebe
o usuário autenticado e só enxerga as conversas dele.
"""

from historico.registro import (
    BANCO,
    PAPEL,
    ConversaGravada,
    ConversaInexistente,
    Historico,
    HistoricoIndisponivel,
    HistoricoNoBanco,
    ItemGravado,
    RespostaParaGravar,
    Situacao,
    historico_do_ambiente,
)

__all__ = [
    "BANCO",
    "PAPEL",
    "ConversaGravada",
    "ConversaInexistente",
    "Historico",
    "HistoricoIndisponivel",
    "HistoricoNoBanco",
    "ItemGravado",
    "RespostaParaGravar",
    "Situacao",
    "historico_do_ambiente",
]
