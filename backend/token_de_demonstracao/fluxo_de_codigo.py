"""O fluxo de código de autorização com PKCE, percorrido por HTTP como um navegador faria.

É a única implementação do percurso: os testes e o comando de token de demonstração a usam. Os
clientes do realm que fazem login não aceitam senha direto (ADR 0004), então quem precisa de um
token real sem abrir um navegador abre a tela de login, envia o formulário e troca o código.
Os clientes registrados dinamicamente pedem também o consentimento do usuário, que o percurso
aceita (ADR 0007).
"""

import base64
import hashlib
import html
import re
import secrets
from dataclasses import dataclass
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

TEMPO_LIMITE_EM_SEGUNDOS = 10


@dataclass(frozen=True)
class Aplicacao:
    """Um cliente do realm que faz login pelo fluxo de código: o identificador, o retorno e os
    escopos que ele pede no login, separados por espaço."""

    identificador: str
    retorno: str
    escopo: str = "openid"


class LoginRecusado(Exception):
    """O provedor não devolveu um código de autorização para o usuário e a senha dados."""


class TelaDeLoginInesperada(Exception):
    """A página que o provedor devolveu não tem o formulário de login esperado."""


def _base(emissor: str) -> str:
    """Os endpoints OpenID Connect do realm, dado o emissor."""
    return f"{emissor}/protocol/openid-connect"


def _novo_verificador() -> str:
    """O segredo do PKCE, que só quem começou o login conhece."""
    return secrets.token_urlsafe(48)


def _desafio_de(verificador: str) -> str:
    """O desafio S256 do PKCE: o hash do verificador, que vai no pedido de autorização."""
    resumo = hashlib.sha256(verificador.encode()).digest()
    return base64.urlsafe_b64encode(resumo).rstrip(b"=").decode()


def abrir_tela_de_login(
    navegador: httpx.Client, emissor: str, aplicacao: Aplicacao, desafio: str
) -> httpx.Response:
    """Pede a autorização como a aplicação faria e devolve a tela de login do provedor."""
    pagina = navegador.get(
        f"{_base(emissor)}/auth",
        params={
            "client_id": aplicacao.identificador,
            "response_type": "code",
            "scope": aplicacao.escopo,
            "redirect_uri": aplicacao.retorno,
            "state": secrets.token_urlsafe(16),
            "code_challenge": desafio,
            "code_challenge_method": "S256",
        },
    )
    pagina.raise_for_status()
    return pagina


def enviar_credenciais(
    navegador: httpx.Client,
    emissor: str,
    aplicacao: Aplicacao,
    desafio: str,
    nome_de_usuario: str,
    senha: str,
) -> httpx.Response:
    """Preenche o formulário da tela de login e devolve a resposta do provedor, sem segui-la."""
    pagina = abrir_tela_de_login(navegador, emissor, aplicacao, desafio)
    acao = re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', pagina.text)
    if not acao:
        raise TelaDeLoginInesperada("a página de login não tem o formulário esperado")
    return navegador.post(
        html.unescape(acao.group(1)),
        data={"username": nome_de_usuario, "password": senha},
        headers={"Cookie": _cookies(navegador)},
    )


def _cookies(navegador: httpx.Client) -> str:
    """O cabeçalho `Cookie` da sessão de login no provedor.

    O provedor marca os cookies como Secure. Navegadores os enviam em localhost mesmo sem HTTPS;
    o cookiejar do Python não, então o cabeçalho é montado aqui.
    """
    return "; ".join(f"{c.name}={c.value}" for c in navegador.cookies.jar)


def consentir(navegador: httpx.Client, resposta: httpx.Response) -> httpx.Response:
    """Aceita a tela de consentimento, se o provedor a pedir depois das credenciais, e devolve a
    resposta seguinte, sem segui-la. Sem pedido de consentimento, devolve a mesma resposta.

    O provedor pede o consentimento aos clientes registrados dinamicamente: o usuário vê que um
    assistente quer acesso em nome dele e confirma.
    """
    destino = resposta.headers.get("location", "")
    if resposta.status_code != 302 or "/login-actions/required-action" not in destino:
        return resposta
    tela = navegador.get(destino, headers={"Cookie": _cookies(navegador)})
    tela.raise_for_status()
    formulario = re.search(
        r'id="kc-oauth".*?<form[^>]*action="([^"]+)"(.*?)</form>', tela.text, re.S
    )
    if not formulario:
        raise TelaDeLoginInesperada("a tela de consentimento não tem o formulário esperado")
    ocultos = dict(
        re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', formulario.group(2))
    )
    return navegador.post(
        urljoin(destino, html.unescape(formulario.group(1))),
        data={**ocultos, "accept": "Sim"},
        headers={"Cookie": _cookies(navegador)},
    )


def pedir_tokens(emissor: str, dados: dict[str, str]) -> dict[str, str]:
    """Pede tokens ao endpoint de token do realm e devolve a resposta do provedor."""
    resposta = httpx.post(f"{_base(emissor)}/token", data=dados, timeout=TEMPO_LIMITE_EM_SEGUNDOS)
    resposta.raise_for_status()
    return resposta.json()


def troca_do_codigo(
    emissor: str, aplicacao: Aplicacao, nome_de_usuario: str, senha: str
) -> dict[str, str]:
    """Faz login como um navegador e devolve o pedido, ainda não enviado, que troca o código de
    autorização por tokens no endpoint de token.

    Levanta `LoginRecusado` se o provedor não devolver o código de autorização.
    """
    verificador = _novo_verificador()
    with httpx.Client(timeout=TEMPO_LIMITE_EM_SEGUNDOS) as navegador:
        resposta = consentir(
            navegador,
            enviar_credenciais(
                navegador, emissor, aplicacao, _desafio_de(verificador), nome_de_usuario, senha
            ),
        )
    destino = resposta.headers.get("location", "")
    if resposta.status_code != 302 or not destino.startswith(aplicacao.retorno):
        raise LoginRecusado(nome_de_usuario)
    return {
        "grant_type": "authorization_code",
        "client_id": aplicacao.identificador,
        "code": parse_qs(urlparse(destino).query)["code"][0],
        "redirect_uri": aplicacao.retorno,
        "code_verifier": verificador,
    }


def tokens_pelo_fluxo_de_codigo(
    emissor: str, aplicacao: Aplicacao, nome_de_usuario: str, senha: str
) -> dict[str, str]:
    """Faz login como um navegador e devolve a resposta do provedor: token de acesso e outros.

    Levanta `LoginRecusado` se o provedor não devolver o código de autorização.
    """
    return pedir_tokens(emissor, troca_do_codigo(emissor, aplicacao, nome_de_usuario, senha))
