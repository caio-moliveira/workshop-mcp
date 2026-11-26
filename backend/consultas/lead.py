"""O canal e a etapa do funil de um lead: as duas enumerações fechadas do Comercial (glossário)."""

from enum import StrEnum

from consultas.periodo import ParametroInvalido


class Canal(StrEnum):
    """O meio pelo qual um lead chegou."""

    INDICACAO = "Indicação"
    ORGANICO = "Orgânico"
    MIDIA_PAGA = "Mídia paga"
    EVENTOS = "Eventos"
    PROSPECCAO_ATIVA = "Prospecção ativa"

    @classmethod
    def ler(cls, valor: str) -> "Canal":
        """O canal de um valor recebido de fora, com a grafia exata, ou ParametroInvalido."""
        try:
            return cls(valor)
        except ValueError as erro:
            raise ParametroInvalido("canal fora da enumeração") from erro


class Etapa(StrEnum):
    """A posição de um lead na negociação, na ordem do funil, com Perdido por último."""

    NOVO = "Novo"
    CONTATADO = "Contatado"
    QUALIFICADO = "Qualificado"
    PROPOSTA = "Proposta"
    FECHADO = "Fechado"
    PERDIDO = "Perdido"

    @classmethod
    def ler(cls, valor: str) -> "Etapa":
        """A etapa de um valor recebido de fora, com a grafia exata, ou ParametroInvalido."""
        try:
            return cls(valor)
        except ValueError as erro:
            raise ParametroInvalido("etapa fora da enumeração") from erro
