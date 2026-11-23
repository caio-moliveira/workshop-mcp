"""Auxiliares dos testes: tokens forjados com uma chave local, para os casos que o provedor
real não emite (assinatura alheia, emissor errado, perfil inválido)."""

import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from provedor import DESTINATARIO_DA_API, emissor

IDENTIFICADOR_DA_CHAVE = "chave-local"


def nova_chave() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class ChavesLocais:
    """Origem de chaves que confia em uma única chave pública local."""

    def __init__(self, chave_privada: rsa.RSAPrivateKey) -> None:
        self._publica = chave_privada.public_key()

    def chave_para(self, token: str):
        return self._publica


def conteudo_valido(**sobreposicoes) -> dict:
    """O conteúdo de um token que a API aceitaria, com os campos trocados à vontade.

    Um campo com valor None é removido.
    """
    agora = int(time.time())
    conteudo = {
        "iss": emissor(),
        "aud": DESTINATARIO_DA_API,
        "sub": str(uuid.uuid4()),
        "name": "Ana Ribeiro",
        "perfil": "vendas",
        "iat": agora,
        "nbf": agora,
        "exp": agora + 300,
    }
    conteudo.update(sobreposicoes)
    return {chave: valor for chave, valor in conteudo.items() if valor is not None}


def assinar(conteudo: dict, chave: rsa.RSAPrivateKey, algoritmo: str = "RS256") -> str:
    return jwt.encode(conteudo, chave, algorithm=algoritmo, headers={"kid": IDENTIFICADOR_DA_CHAVE})
