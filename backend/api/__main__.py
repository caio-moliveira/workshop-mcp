"""Sobe a API com a configuração do ambiente: python -m api."""

import logging
import os
from pathlib import Path

import uvicorn

from acesso.provedor import DESTINATARIO_DA_API, configuracao_do_ambiente
from api import criar_aplicacao
from assistente import limites_do_ambiente, modelo_do_ambiente
from consultas import ExecutorDeConsultas, banco_do_ambiente, credenciais_do_ambiente
from historico import historico_do_ambiente

# Onde a API lê a última execução de aceite: a pasta que o compose monta só para leitura.
PASTA_PADRAO_DA_EXECUCAO_DE_ACEITE = "/execucao-de-aceite"


def execucao_de_aceite_do_ambiente() -> Path | None:
    """A pasta da execução de aceite, só com o interruptor de demonstração ligado
    (PAINEL_DE_SEGURANCA=ligado). Desligado, o padrão, o painel de segurança não existe."""
    if os.environ.get("PAINEL_DE_SEGURANCA", "").strip().lower() != "ligado":
        return None
    return Path(os.environ.get("PASTA_DA_EXECUCAO_DE_ACEITE") or PASTA_PADRAO_DA_EXECUCAO_DE_ACEITE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with (
        ExecutorDeConsultas(banco_do_ambiente(), credenciais_do_ambiente()) as consultas,
        historico_do_ambiente() as historico,
    ):
        aplicacao = criar_aplicacao(
            configuracao_do_ambiente(DESTINATARIO_DA_API),
            origem_do_frontend=os.environ["ENDERECO_DO_FRONTEND"],
            consultas=consultas,
            modelo=modelo_do_ambiente(),
            endereco_do_mcp=os.environ["ENDERECO_INTERNO_DO_MCP"],
            limites=limites_do_ambiente(),
            historico=historico,
            execucao_de_aceite=execucao_de_aceite_do_ambiente(),
        )
        uvicorn.run(aplicacao, host="0.0.0.0", port=8000)
