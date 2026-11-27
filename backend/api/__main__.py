"""Sobe a API com a configuração do ambiente: python -m api."""

import logging
import os
from contextlib import ExitStack

import uvicorn

from aceite import execucao_de_aceite_do_ambiente
from acesso.provedor import DESTINATARIO_DA_API, configuracao_do_ambiente
from api import criar_aplicacao
from assistente import limites_do_ambiente, modelo_do_ambiente
from auditoria import leitura_da_auditoria_do_ambiente
from consultas import ExecutorDeConsultas, banco_do_ambiente, credenciais_do_ambiente
from historico import historico_do_ambiente

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    execucao_de_aceite = execucao_de_aceite_do_ambiente()
    with (
        ExecutorDeConsultas(banco_do_ambiente(), credenciais_do_ambiente()) as consultas,
        historico_do_ambiente() as historico,
        ExitStack() as pilha,
    ):
        # Só com o interruptor de demonstração ligado a API lê a auditoria (ADR 0012).
        leitura_da_auditoria = (
            pilha.enter_context(leitura_da_auditoria_do_ambiente())
            if execucao_de_aceite is not None
            else None
        )
        aplicacao = criar_aplicacao(
            configuracao_do_ambiente(DESTINATARIO_DA_API),
            origem_do_frontend=os.environ["ENDERECO_DO_FRONTEND"],
            consultas=consultas,
            modelo=modelo_do_ambiente(),
            endereco_do_mcp=os.environ["ENDERECO_INTERNO_DO_MCP"],
            limites=limites_do_ambiente(),
            historico=historico,
            execucao_de_aceite=execucao_de_aceite,
            leitura_da_auditoria=leitura_da_auditoria,
        )
        uvicorn.run(aplicacao, host="0.0.0.0", port=8000)
