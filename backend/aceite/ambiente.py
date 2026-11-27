"""Onde a API lê a execução de aceite, pela configuração: o interruptor de demonstração."""

import os
from pathlib import Path

# Onde a API lê a última execução de aceite: a pasta que o compose monta só para leitura.
PASTA_PADRAO_DA_EXECUCAO_DE_ACEITE = "/execucao-de-aceite"


def execucao_de_aceite_do_ambiente() -> Path | None:
    """A pasta da execução de aceite, só com o interruptor de demonstração ligado
    (PAINEL_DE_SEGURANCA=ligado). Desligado, o padrão, o painel de segurança não existe."""
    if os.environ.get("PAINEL_DE_SEGURANCA", "").strip().lower() != "ligado":
        return None
    return Path(os.environ.get("PASTA_DA_EXECUCAO_DE_ACEITE") or PASTA_PADRAO_DA_EXECUCAO_DE_ACEITE)
