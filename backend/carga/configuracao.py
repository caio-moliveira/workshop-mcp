"""Configuração do gerador: semente e data de referência."""

import os
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent / "configuracao.toml"


@dataclass(frozen=True)
class Configuracao:
    semente: int
    data_referencia: date


def ler_configuracao() -> Configuracao:
    """Lê o arquivo versionado; variáveis de ambiente sobrepõem seus valores."""
    valores = tomllib.loads(ARQUIVO.read_text(encoding="utf-8"))
    semente = int(os.environ.get("SEMENTE", valores["semente"]))
    data_referencia = valores["data_referencia"]
    if "DATA_REFERENCIA" in os.environ:
        data_referencia = date.fromisoformat(os.environ["DATA_REFERENCIA"])
    return Configuracao(semente=semente, data_referencia=data_referencia)
