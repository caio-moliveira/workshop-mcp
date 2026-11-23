"""A janela de tempo dos dados, sempre derivada da data de referência."""

from dataclasses import dataclass
from datetime import date, timedelta

MESES_DE_OPERACAO = 24
MESES_DE_FUNIL_ANTES_DA_JANELA = 3


def somar_meses(dia: date, meses: int) -> date:
    """Soma meses a uma data que cai no dia 1 do mês."""
    indice = dia.year * 12 + (dia.month - 1) + meses
    return date(indice // 12, indice % 12 + 1, 1)


def dias_entre(inicio: date, fim: date) -> list[date]:
    """Todos os dias de inicio a fim, inclusive."""
    return [inicio + timedelta(days=n) for n in range((fim - inicio).days + 1)]


@dataclass(frozen=True)
class Calendario:
    """Datas-limite dos dados: nada acontece depois da data de referência."""

    data_referencia: date

    @property
    def inicio_da_janela(self) -> date:
        """Primeiro dia dos 24 meses de operação que terminam na data de referência."""
        primeiro_do_mes_seguinte = somar_meses(self.data_referencia.replace(day=1), 1)
        return somar_meses(primeiro_do_mes_seguinte, -MESES_DE_OPERACAO)

    @property
    def inicio_do_funil(self) -> date:
        """O funil comercial começa antes da janela, para haver lojistas no primeiro mês."""
        return somar_meses(self.inicio_da_janela, -MESES_DE_FUNIL_ANTES_DA_JANELA)
