"""Onde o provedor de identidade publica o que a validação precisa: o emissor e as chaves."""

REALM = "pulso"
# O destinatário (aud) que um token precisa trazer para ser aceito pela API.
DESTINATARIO_DA_API = "pulso-api"


def emissor_em(endereco_do_provedor: str) -> str:
    """O emissor (iss) dos tokens do realm, dado o endereço do provedor."""
    return f"{endereco_do_provedor}/realms/{REALM}"


def url_das_chaves_em(endereco_do_provedor: str) -> str:
    """Onde o realm publica as chaves públicas, dado o endereço do provedor."""
    return f"{emissor_em(endereco_do_provedor)}/protocol/openid-connect/certs"
