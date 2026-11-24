"""Onde o provedor de identidade publica o que a validação precisa: o emissor e as chaves."""

import os

from acesso.validacao import ChavesDoProvedor, ConfiguracaoDeAcesso

REALM = "pulso"
# O destinatário (aud) que um token precisa trazer para ser aceito pela API.
DESTINATARIO_DA_API = "pulso-api"
# O destinatário que um token precisa trazer para ser aceito pelo servidor MCP (ADR 0006).
DESTINATARIO_DO_MCP = "pulso-mcp"


def emissor_em(endereco_do_provedor: str) -> str:
    """O emissor (iss) dos tokens do realm, dado o endereço do provedor."""
    return f"{endereco_do_provedor}/realms/{REALM}"


def url_das_chaves_em(endereco_do_provedor: str) -> str:
    """Onde o realm publica as chaves públicas, dado o endereço do provedor."""
    return f"{emissor_em(endereco_do_provedor)}/protocol/openid-connect/certs"


def configuracao_do_ambiente(destinatario: str) -> ConfiguracaoDeAcesso:
    """A validação de um serviço do compose, que aceita tokens para o destinatário dado.

    O emissor é o endereço público do provedor (ENDERECO_PUBLICO_DO_PROVEDOR); as chaves vêm pela
    rede interna (ENDERECO_INTERNO_DO_PROVEDOR).
    """
    return ConfiguracaoDeAcesso(
        emissor=emissor_em(os.environ["ENDERECO_PUBLICO_DO_PROVEDOR"]),
        destinatario=destinatario,
        chaves=ChavesDoProvedor(url_das_chaves_em(os.environ["ENDERECO_INTERNO_DO_PROVEDOR"])),
    )
