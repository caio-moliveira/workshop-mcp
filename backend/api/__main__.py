"""Sobe a API com a configuração do ambiente: python -m api."""

import logging
import os

import uvicorn

from acesso import ChavesDoProvedor, ConfiguracaoDeAcesso
from api import criar_aplicacao

REALM = "pulso"
DESTINATARIO = "pulso-api"


def configuracao_do_ambiente() -> ConfiguracaoDeAcesso:
    """O emissor é o endereço público do provedor; as chaves vêm pela rede interna."""
    return ConfiguracaoDeAcesso(
        emissor=f"{os.environ['ENDERECO_PUBLICO_DO_PROVEDOR']}/realms/{REALM}",
        destinatario=DESTINATARIO,
        chaves=ChavesDoProvedor(
            f"{os.environ['ENDERECO_INTERNO_DO_PROVEDOR']}/realms/{REALM}"
            "/protocol/openid-connect/certs"
        ),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(criar_aplicacao(configuracao_do_ambiente()), host="0.0.0.0", port=8000)
