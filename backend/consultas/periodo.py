"""O período de um painel: a janela de dias que termina na data de referência (glossário)."""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class ParametroInvalido(Exception):
    """Um parâmetro fora do previsto. O motivo é só para o log, nunca para quem chamou (RS-08)."""


class Periodo(StrEnum):
    TRINTA_DIAS = "30d"
    NOVENTA_DIAS = "90d"
    DOZE_MESES = "12m"
    VINTE_E_QUATRO_MESES = "24m"

    @classmethod
    def ler(cls, valor: str) -> "Periodo":
        """O período de um valor recebido de fora, ou ParametroInvalido."""
        try:
            return cls(valor)
        except ValueError as erro:
            raise ParametroInvalido("período fora da enumeração") from erro


PERIODO_PADRAO = Periodo.DOZE_MESES

_DIAS = {Periodo.TRINTA_DIAS: 30, Periodo.NOVENTA_DIAS: 90}
_MESES = {Periodo.DOZE_MESES: 12, Periodo.VINTE_E_QUATRO_MESES: 24}


@dataclass(frozen=True)
class Intervalo:
    """Dias de `inicio` a `fim`, inclusive, no horário de Brasília."""

    inicio: date
    fim: date

    def anterior(self, periodo: Periodo) -> "Intervalo":
        """O intervalo de mesmo tamanho que termina na véspera deste."""
        return terminado_em(periodo, self.inicio - timedelta(days=1))


def _menos_meses(dia: date, meses: int) -> date:
    """O mesmo dia, `meses` antes; no fim de um mês mais curto, o último dia dele."""
    indice = dia.year * 12 + (dia.month - 1) - meses
    ano, mes = divmod(indice, 12)
    ultimo_dia = calendar.monthrange(ano, mes + 1)[1]
    return date(ano, mes + 1, min(dia.day, ultimo_dia))


def terminado_em(periodo: Periodo, fim: date) -> Intervalo:
    """Os últimos 30 ou 90 dias, ou 12 ou 24 meses, terminando em `fim` (inclusive)."""
    if periodo in _DIAS:
        return Intervalo(fim - timedelta(days=_DIAS[periodo] - 1), fim)
    return Intervalo(_menos_meses(fim, _MESES[periodo]) + timedelta(days=1), fim)
