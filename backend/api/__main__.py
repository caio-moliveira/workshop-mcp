"""Sobe a API com a configuração do ambiente: python -m api."""

import logging
import os

import uvicorn

from acesso.provedor import DESTINATARIO_DA_API, configuracao_do_ambiente
from api import criar_aplicacao
from consultas import ExecutorDeConsultas, banco_do_ambiente, credenciais_do_ambiente

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with ExecutorDeConsultas(banco_do_ambiente(), credenciais_do_ambiente()) as consultas:
        aplicacao = criar_aplicacao(
            configuracao_do_ambiente(DESTINATARIO_DA_API),
            origem_do_frontend=os.environ["ENDERECO_DO_FRONTEND"],
            consultas=consultas,
        )
        uvicorn.run(aplicacao, host="0.0.0.0", port=8000)
