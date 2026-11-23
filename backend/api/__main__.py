"""Sobe a API com a configuração do ambiente: python -m api."""

import logging
import os

import uvicorn

from acesso import ChavesDoProvedor, ConfiguracaoDeAcesso
from acesso.provedor import DESTINATARIO_DA_API, emissor_em, url_das_chaves_em
from api import criar_aplicacao


def configuracao_do_ambiente() -> ConfiguracaoDeAcesso:
    """O emissor é o endereço público do provedor; as chaves vêm pela rede interna."""
    return ConfiguracaoDeAcesso(
        emissor=emissor_em(os.environ["ENDERECO_PUBLICO_DO_PROVEDOR"]),
        destinatario=DESTINATARIO_DA_API,
        chaves=ChavesDoProvedor(url_das_chaves_em(os.environ["ENDERECO_INTERNO_DO_PROVEDOR"])),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    aplicacao = criar_aplicacao(
        configuracao_do_ambiente(), origem_do_frontend=os.environ["ENDERECO_DO_FRONTEND"]
    )
    uvicorn.run(aplicacao, host="0.0.0.0", port=8000)
