"""O canal e a etapa do funil de um lead: as duas enumerações fechadas do Comercial (glossário)."""

from enum import StrEnum
from typing import Self

from consultas.periodo import ParametroInvalido


class _EnumeracaoDoLead(StrEnum):
    """Uma enumeração fechada do lead, lida de fora com a grafia exata."""

    @classmethod
    def ler(cls, valor: str) -> Self:
        """O membro de um valor recebido de fora, com a grafia exata, ou ParametroInvalido."""
        try:
            return cls(valor)
        except ValueError as erro:
            raise ParametroInvalido(f"{cls.__name__.lower()} fora da enumeração") from erro


class Canal(_EnumeracaoDoLead):
    """O meio pelo qual um lead chegou."""

    INDICACAO = "Indicação"
    ORGANICO = "Orgânico"
    MIDIA_PAGA = "Mídia paga"
    EVENTOS = "Eventos"
    PROSPECCAO_ATIVA = "Prospecção ativa"


class Etapa(_EnumeracaoDoLead):
    """A posição de um lead na negociação, na ordem do funil, com Perdido por último."""

    NOVO = "Novo"
    CONTATADO = "Contatado"
    QUALIFICADO = "Qualificado"
    PROPOSTA = "Proposta"
    FECHADO = "Fechado"
    PERDIDO = "Perdido"


# Lead em negociação: ainda não fechou nem foi perdido (glossário).
ETAPAS_EM_NEGOCIACAO = tuple(
    etapa for etapa in Etapa if etapa not in (Etapa.FECHADO, Etapa.PERDIDO)
)
