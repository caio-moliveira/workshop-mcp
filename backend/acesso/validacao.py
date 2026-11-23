"""Validação do token de acesso emitido pelo provedor de identidade."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

import jwt

# Folga para diferenças de relógio entre o provedor e quem valida.
FOLGA_DE_RELOGIO_EM_SEGUNDOS = 5


class Perfil(StrEnum):
    VENDAS = "vendas"
    PRODUTOS = "produtos"
    COMERCIAL = "comercial"
    DIRETORIA = "diretoria"


@dataclass(frozen=True)
class UsuarioAutenticado:
    id: str
    nome: str
    perfil: Perfil


class TokenRecusado(Exception):
    """O token não prova quem é o usuário. O motivo é só para o log, nunca para quem chamou."""


class OrigemDeChaves(Protocol):
    """De onde vem a chave pública que confere a assinatura de um token."""

    def chave_para(self, token: str): ...


class ChavesDoProvedor:
    """As chaves públicas publicadas pelo provedor, buscadas pela URL e mantidas em cache."""

    def __init__(self, url: str) -> None:
        # Uma chave com identificador desconhecido força nova busca (rotação de chaves).
        self._cliente = jwt.PyJWKClient(url, cache_keys=True, timeout=5)

    def chave_para(self, token: str):
        return self._cliente.get_signing_key_from_jwt(token).key


@dataclass(frozen=True)
class ConfiguracaoDeAcesso:
    emissor: str
    destinatario: str
    chaves: OrigemDeChaves
    # Segundos desde a época. Injetável para que os testes vejam um token real vencer.
    relogio: Callable[[], float] = field(default=time.time)


def autenticar(token: str, configuracao: ConfiguracaoDeAcesso) -> UsuarioAutenticado:
    """Devolve o usuário autenticado pelo token ou levanta TokenRecusado."""
    try:
        conteudo = jwt.decode(
            token,
            configuracao.chaves.chave_para(token),
            algorithms=["RS256"],
            issuer=configuracao.emissor,
            audience=configuracao.destinatario,
            # A validade é conferida abaixo, com o relógio da configuração.
            options={
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
                "require": ["iss", "aud", "sub", "exp", "name"],
            },
        )
    except jwt.PyJWTError as erro:
        raise TokenRecusado(str(erro)) from erro
    _conferir_validade(conteudo, configuracao.relogio())
    return UsuarioAutenticado(
        id=conteudo["sub"], nome=conteudo["name"], perfil=_perfil_do_token(conteudo)
    )


def _perfil_do_token(conteudo: dict) -> Perfil:
    """O perfil vem só da claim `perfil`, que traz exatamente um perfil conhecido (RS-03)."""
    perfil = conteudo.get("perfil")
    if not isinstance(perfil, str) or perfil not in Perfil:
        raise TokenRecusado(f"claim perfil inválida: {perfil!r}")
    return Perfil(perfil)


def _conferir_validade(conteudo: dict, agora: float) -> None:
    vencimento, inicio = conteudo["exp"], conteudo.get("nbf", 0)
    if not all(isinstance(data, int | float) for data in (vencimento, inicio)):
        raise TokenRecusado("exp ou nbf não é um número")
    if agora > vencimento + FOLGA_DE_RELOGIO_EM_SEGUNDOS:
        raise TokenRecusado("token vencido")
    if agora < inicio - FOLGA_DE_RELOGIO_EM_SEGUNDOS:
        raise TokenRecusado("token ainda não é válido")
