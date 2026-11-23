"""Auxiliares dos testes: tokens reais do provedor de identidade.

Os tokens vêm do fluxo de código de autorização com PKCE, percorrido por HTTP como um navegador
faria. Nenhum cliente do realm aceita senha direto para servir aos testes (ADR 0004).
"""

import base64
import hashlib
import html
import re
import secrets
from urllib.parse import parse_qs, urlparse

import httpx
from apoio import _variavel

REALM = "pulso"
CLIENTE_DA_APLICACAO = "pulso-web"
DESTINATARIO_DA_API = "pulso-api"

# Nome de usuário, variável da senha, nome de exibição e perfil de cada usuário de demonstração.
USUARIOS_DE_DEMONSTRACAO = [
    ("ana.vendas", "SENHA_DO_USUARIO_VENDAS", "Ana Ribeiro", "vendas"),
    ("bruno.produtos", "SENHA_DO_USUARIO_PRODUTOS", "Bruno Costa", "produtos"),
    ("carla.comercial", "SENHA_DO_USUARIO_COMERCIAL", "Carla Mendes", "comercial"),
    ("diego.diretoria", "SENHA_DO_USUARIO_DIRETORIA", "Diego Almeida", "diretoria"),
]


def emissor() -> str:
    """O emissor dos tokens: o endereço público do provedor, no realm do projeto."""
    return f"{_variavel('ENDERECO_PUBLICO_DO_PROVEDOR')}/realms/{REALM}"


def url_das_chaves() -> str:
    """Onde o provedor publica as chaves públicas, alcançado da máquina local."""
    return f"{emissor()}/protocol/openid-connect/certs"


def senha_de(usuario: str) -> str:
    variavel = next(v for u, v, _, _ in USUARIOS_DE_DEMONSTRACAO if u == usuario)
    return _variavel(variavel)


class LoginRecusado(Exception):
    """O provedor não devolveu um código de autorização para as credenciais dadas."""


def token_pelo_fluxo_de_codigo(usuario: str, senha: str) -> str:
    """Faz login como um navegador, pelo fluxo de código com PKCE, e devolve o token de acesso."""
    retorno = f"{_variavel('ENDERECO_DO_FRONTEND')}/"
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
                "client_id": CLIENTE_DA_APLICACAO,
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
                "client_id": CLIENTE_DA_APLICACAO,
                "code": codigo,
                "redirect_uri": retorno,
                "code_verifier": verificador,
            },
        )
        token.raise_for_status()
        return token.json()["access_token"]


def token_de_outro_servico(usuario: str, senha: str) -> str:
    """Um token do mesmo provedor e do mesmo usuário, mas emitido para outro serviço.

    O `admin-cli` existe em todo realm e não traz a API entre os destinatários.
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
