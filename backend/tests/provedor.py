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
from acesso.provedor import DESTINATARIO_DA_API, REALM, emissor_em, url_das_chaves_em

__all__ = ["DESTINATARIO_DA_API", "REALM"]

APLICACAO = "pulso-web"


@dataclass(frozen=True)
class UsuarioDeDemonstracao:
    nome_de_usuario: str
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


def senha_de(nome_de_usuario: str) -> str:
    return next(u for u in USUARIOS_DE_DEMONSTRACAO if u.nome_de_usuario == nome_de_usuario).senha()


class LoginRecusado(Exception):
    """O provedor não devolveu um código de autorização para o usuário e a senha dados."""


def _retorno() -> str:
    return f"{variavel('ENDERECO_DO_FRONTEND')}/"


def _base(emissor_do_realm: str | None = None) -> str:
    """Os endpoints OpenID Connect de um realm; por padrão, o realm da aplicação."""
    return f"{emissor_do_realm or emissor()}/protocol/openid-connect"


def _pedir_tokens(dados: dict[str, str], emissor_do_realm: str | None = None) -> dict[str, str]:
    """Pede tokens ao endpoint de token do realm e devolve a resposta do provedor."""
    resposta = httpx.post(f"{_base(emissor_do_realm)}/token", data=dados, timeout=10)
    resposta.raise_for_status()
    return resposta.json()


def _pedir_token(dados: dict[str, str], emissor_do_realm: str | None = None) -> str:
    """Só o token de acesso da resposta de `_pedir_tokens`."""
    return _pedir_tokens(dados, emissor_do_realm)["access_token"]


def _abrir_tela_de_login(navegador: httpx.Client, desafio: str) -> httpx.Response:
    """Pede a autorização como a aplicação faria e devolve a tela de login do provedor."""
    pagina = navegador.get(
        f"{_base()}/auth",
        params={
            "client_id": APLICACAO,
            "response_type": "code",
            "scope": "openid",
            "redirect_uri": _retorno(),
            "state": secrets.token_urlsafe(16),
            "code_challenge": desafio,
            "code_challenge_method": "S256",
        },
    )
    pagina.raise_for_status()
    return pagina


def _enviar_credenciais(
    navegador: httpx.Client, desafio: str, nome_de_usuario: str, senha: str
) -> httpx.Response:
    """Preenche o formulário da tela de login e devolve a resposta do provedor, sem segui-la."""
    pagina = _abrir_tela_de_login(navegador, desafio)
    acao = re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', pagina.text)
    assert acao, "a página de login não tem o formulário esperado"
    # O provedor marca os cookies como Secure. Navegadores os enviam em localhost mesmo sem
    # HTTPS; o cookiejar do Python não, então o cabeçalho é montado aqui.
    cookies = "; ".join(f"{c.name}={c.value}" for c in pagina.cookies.jar)
    return navegador.post(
        html.unescape(acao.group(1)),
        data={"username": nome_de_usuario, "password": senha},
        headers={"Cookie": cookies},
    )


def tela_de_login() -> str:
    """O HTML da tela de login, como o navegador o recebe ao entrar na aplicação."""
    with httpx.Client(timeout=10) as navegador:
        return _abrir_tela_de_login(navegador, secrets.token_urlsafe(43)).text


def tela_apos_credenciais(
    nome_de_usuario: str, senha: str, navegador: httpx.Client | None = None
) -> str:
    """O HTML que o provedor devolve depois de um envio de credenciais que não entra.

    Passe um `navegador` para enviar várias tentativas pela mesma conexão, em sequência rápida.
    """
    if navegador is None:
        with httpx.Client(timeout=10) as novo:
            return tela_apos_credenciais(nome_de_usuario, senha, novo)
    resposta = _enviar_credenciais(navegador, secrets.token_urlsafe(43), nome_de_usuario, senha)
    assert resposta.status_code == 200, "o provedor aceitou as credenciais"
    return resposta.text


def token_pelo_fluxo_de_codigo(nome_de_usuario: str, senha: str) -> str:
    """Faz login como um navegador, pelo fluxo de código com PKCE, e devolve o token de acesso."""
    return tokens_pelo_fluxo_de_codigo(nome_de_usuario, senha)["access_token"]


def tokens_pelo_fluxo_de_codigo(nome_de_usuario: str, senha: str) -> dict[str, str]:
    """O mesmo login, devolvendo a resposta inteira do provedor: token de acesso, de id e outros."""
    verificador = secrets.token_urlsafe(48)
    desafio = (
        base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    with httpx.Client(timeout=10) as navegador:
        resposta = _enviar_credenciais(navegador, desafio, nome_de_usuario, senha)
    destino = resposta.headers.get("location", "")
    if resposta.status_code != 302 or not destino.startswith(_retorno()):
        raise LoginRecusado(nome_de_usuario)
    return _pedir_tokens(
        {
            "grant_type": "authorization_code",
            "client_id": APLICACAO,
            "code": parse_qs(urlparse(destino).query)["code"][0],
            "redirect_uri": _retorno(),
            "code_verifier": verificador,
        }
    )


def token_de_outro_servico(nome_de_usuario: str, senha: str) -> str:
    """Um token do mesmo provedor e do mesmo usuário, mas emitido para outro serviço.

    O `admin-cli` existe em todo realm, aceita senha direto e não traz a API entre os
    destinatários. É a única exceção ao fluxo de código, e serve só para obter um token realista
    de "mesmo provedor, outro serviço" sem criar no realm um cliente só para os testes.
    """
    return _pedir_token(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": nome_de_usuario,
            "password": senha,
        }
    )


def _token_de_administrador() -> str:
    """Token do administrador do Keycloak, emitido pelo realm `master`."""
    return _pedir_token(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": variavel("KC_BOOTSTRAP_ADMIN_USERNAME"),
            "password": variavel("KC_BOOTSTRAP_ADMIN_PASSWORD"),
        },
        emissor_do_realm=f"{endereco_do_provedor()}/realms/master",
    )


def administracao() -> httpx.Client:
    """Cliente HTTP da API de administração do realm da aplicação, já com o token do administrador.

    Use com `with`: os caminhos são relativos ao realm (`/users`, ...). O token de administrador
    vale pouco tempo; abra um por teste.
    """
    return httpx.Client(
        base_url=f"{endereco_do_provedor()}/admin/realms/{REALM}",
        headers={"Authorization": f"Bearer {_token_de_administrador()}"},
        timeout=10,
    )
