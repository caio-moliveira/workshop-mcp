"""Auxiliares dos testes: tokens reais do provedor de identidade.

Os tokens da aplicação vêm do fluxo de código de autorização com PKCE, percorrido por HTTP como
um navegador faria: o cliente `pulso-web` não aceita senha direto (ADR 0004).
"""

import base64
import hashlib
import html
import re
import secrets
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx
from apoio import variavel

from acesso import Perfil
from acesso.provedor import DESTINATARIO_DA_API, emissor_em, url_das_chaves_em

__all__ = ["DESTINATARIO_DA_API"]

APLICACAO = "pulso-web"


@dataclass(frozen=True)
class UsuarioDeDemonstracao:
    usuario: str
    variavel_da_senha: str
    nome: str
    perfil: Perfil

    def senha(self) -> str:
        return variavel(self.variavel_da_senha)


USUARIOS_DE_DEMONSTRACAO = [
    UsuarioDeDemonstracao("ana.vendas", "SENHA_DO_USUARIO_VENDAS", "Ana Ribeiro", Perfil.VENDAS),
    UsuarioDeDemonstracao(
        "bruno.produtos", "SENHA_DO_USUARIO_PRODUTOS", "Bruno Costa", Perfil.PRODUTOS
    ),
    UsuarioDeDemonstracao(
        "carla.comercial", "SENHA_DO_USUARIO_COMERCIAL", "Carla Mendes", Perfil.COMERCIAL
    ),
    UsuarioDeDemonstracao(
        "diego.diretoria", "SENHA_DO_USUARIO_DIRETORIA", "Diego Almeida", Perfil.DIRETORIA
    ),
]


def endereco_do_provedor() -> str:
    """O endereço público do provedor, como o navegador o alcança."""
    return variavel("ENDERECO_PUBLICO_DO_PROVEDOR")


def emissor() -> str:
    return emissor_em(endereco_do_provedor())


def url_das_chaves() -> str:
    """Onde o provedor publica as chaves públicas, alcançado da máquina local."""
    return url_das_chaves_em(endereco_do_provedor())


def senha_de(usuario: str) -> str:
    return next(u for u in USUARIOS_DE_DEMONSTRACAO if u.usuario == usuario).senha()


class LoginRecusado(Exception):
    """O provedor não devolveu um código de autorização para o usuário e a senha dados."""


def token_pelo_fluxo_de_codigo(usuario: str, senha: str) -> str:
    """Faz login como um navegador, pelo fluxo de código com PKCE, e devolve o token de acesso."""
    retorno = f"{variavel('ENDERECO_DO_FRONTEND')}/"
    verificador = secrets.token_urlsafe(48)
    desafio = (
        base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    base = f"{emissor()}/protocol/openid-connect"
    with httpx.Client(timeout=10) as navegador:
        pagina = navegador.get(
            f"{base}/auth",
            params={
                "client_id": APLICACAO,
                "response_type": "code",
                "scope": "openid",
                "redirect_uri": retorno,
                "state": secrets.token_urlsafe(16),
                "code_challenge": desafio,
                "code_challenge_method": "S256",
            },
        )
        pagina.raise_for_status()
        acao = re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', pagina.text)
        assert acao, "a página de login não tem o formulário esperado"
        # O provedor marca os cookies como Secure. Navegadores os enviam em localhost mesmo sem
        # HTTPS; o cookiejar do Python não, então o cabeçalho é montado aqui.
        cookies = "; ".join(f"{c.name}={c.value}" for c in pagina.cookies.jar)
        resposta = navegador.post(
            html.unescape(acao.group(1)),
            data={"username": usuario, "password": senha},
            headers={"Cookie": cookies},
        )
        destino = resposta.headers.get("location", "")
        if resposta.status_code != 302 or not destino.startswith(retorno):
            raise LoginRecusado(usuario)
        codigo = parse_qs(urlparse(destino).query)["code"][0]
        token = navegador.post(
            f"{base}/token",
            data={
                "grant_type": "authorization_code",
                "client_id": APLICACAO,
                "code": codigo,
                "redirect_uri": retorno,
                "code_verifier": verificador,
            },
        )
        token.raise_for_status()
        return token.json()["access_token"]


def token_de_outro_servico(usuario: str, senha: str) -> str:
    """Um token do mesmo provedor e do mesmo usuário, mas emitido para outro serviço.

    O `admin-cli` existe em todo realm, aceita senha direto e não traz a API entre os
    destinatários. É a única exceção ao fluxo de código, e serve só para obter um token realista
    de "mesmo provedor, outro serviço" sem criar no realm um cliente só para os testes.
    """
    resposta = httpx.post(
        f"{emissor()}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": usuario,
            "password": senha,
        },
        timeout=10,
    )
    resposta.raise_for_status()
    return resposta.json()["access_token"]
