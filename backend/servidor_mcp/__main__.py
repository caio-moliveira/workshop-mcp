"""Sobe o servidor MCP com a configuração do ambiente: python -m servidor_mcp."""

import logging
import os

import uvicorn

from acesso.provedor import DESTINATARIO_DO_MCP, configuracao_do_ambiente
from auditoria import auditoria_do_ambiente
from consultas import ExecutorDeConsultas, banco_do_ambiente, credenciais_do_ambiente
from servidor_mcp import criar_aplicacao, limite_do_ambiente

PORTA = 8001


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with (
        ExecutorDeConsultas(banco_do_ambiente(), credenciais_do_ambiente()) as consultas,
        auditoria_do_ambiente() as auditoria,
    ):
        aplicacao = criar_aplicacao(
            configuracao_do_ambiente(DESTINATARIO_DO_MCP),
            consultas,
            auditoria,
            os.environ["ENDERECO_PUBLICO_DO_MCP"],
            limite_do_ambiente(),
        )
        uvicorn.run(aplicacao, host="0.0.0.0", port=PORTA)
