"""Sobe o servidor MCP com a configuração do ambiente: python -m servidor_mcp."""

import logging
import os

import uvicorn

from acesso import ChavesDoProvedor, ConfiguracaoDeAcesso
from acesso.provedor import DESTINATARIO_DO_MCP, emissor_em, url_das_chaves_em
from consultas import BancoDeDados, ExecutorDeConsultas, credenciais_do_ambiente
from servidor_mcp import criar_aplicacao

PORTA = 8001


def configuracao_do_ambiente() -> ConfiguracaoDeAcesso:
    """O emissor é o endereço público do provedor; as chaves vêm pela rede interna."""
    return ConfiguracaoDeAcesso(
        emissor=emissor_em(os.environ["ENDERECO_PUBLICO_DO_PROVEDOR"]),
        destinatario=DESTINATARIO_DO_MCP,
        chaves=ChavesDoProvedor(url_das_chaves_em(os.environ["ENDERECO_INTERNO_DO_PROVEDOR"])),
    )


def banco_do_ambiente() -> BancoDeDados:
    """O banco carregado, pela rede interna do compose."""
    return BancoDeDados(
        host=os.environ["POSTGRES_HOST"],
        porta=int(os.environ.get("POSTGRES_INTERNAL_PORT", "5432")),
        nome=os.environ["BANCO"],
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with ExecutorDeConsultas(banco_do_ambiente(), credenciais_do_ambiente()) as consultas:
        aplicacao = criar_aplicacao(configuracao_do_ambiente(), consultas)
        uvicorn.run(aplicacao, host="0.0.0.0", port=PORTA)
