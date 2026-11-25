"""A duração medida em milissegundos, igual na linha da consulta e no rastreio da resposta."""

import time


def milissegundos_desde(inicio: float) -> int:
    """Os milissegundos desde `inicio`, um instante lido de `time.monotonic()`."""
    return round((time.monotonic() - inicio) * 1000)
