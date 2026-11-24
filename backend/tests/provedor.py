"""Auxiliares dos testes: tokens reais do provedor de identidade.

Os tokens da aplicação vêm do fluxo de código de autorização com PKCE: o cliente `pulso-web` não
aceita senha direto (ADR 0004). O percurso do fluxo mora em `token_de_demonstracao`, fora dos
testes, porque o comando de token de demonstração usa o mesmo; aqui ficam só os atalhos que o
apontam para o provedor do ambiente.
"""

import os
import secrets

import httpx
import jwt
from apoio import variavel

from acesso import Perfil
from acesso.provedor import (
    DESTINATARIO_DA_API,
    DESTINATARIO_DO_MCP,
    REALM,
    emissor_em,
    url_das_chaves_em,
)
from token_de_demonstracao import (
    APLICACAO_WEB,
    INSPECTOR,
    OUTRA_APLICACAO,
    USUARIOS_DE_DEMONSTRACAO,
    Aplicacao,
    LoginRecusado,
    UsuarioDeDemonstracao,
    aplicacoes,
    fluxo_de_codigo,
)

APLICACAO = APLICACAO_WEB
# O proxy reverso reúne o provedor e o servidor MCP num endereço só, publicado na porta local: é
# o endereço que o túnel expõe aos assistentes externos.
PROXY_DO_AMBIENTE = f"http://127.0.0.1:{os.environ.get('PROXY_PORT', '8088')}"
CAMINHO_DO_REGISTRO = "/clients-registrations/openid-connect"

__all__ = [
    "DESTINATARIO_DA_API",
    "DESTINATARIO_DO_MCP",
    "INSPECTOR",
    "OUTRA_APLICACAO",
    "REALM",
    "USUARIOS_DE_DEMONSTRACAO",
    "LoginRecusado",
]


def endereco_do_provedor() -> str:
    """O endereço público do provedor, como o navegador o alcança."""
    return variavel("ENDERECO_PUBLICO_DO_PROVEDOR")


def emissor() -> str:
    return emissor_em(endereco_do_provedor())


def url_das_chaves() -> str:
    """Onde o provedor publica as chaves públicas, alcançado da máquina local."""
    return url_das_chaves_em(endereco_do_provedor())


def realm_pelo_proxy() -> str:
    """O realm alcançado pelo proxy reverso. O emissor dos tokens continua o endereço público."""
    return f"{PROXY_DO_AMBIENTE}/realms/{REALM}"


def usuario_de(perfil: Perfil) -> UsuarioDeDemonstracao:
    """O usuário de demonstração de um perfil."""
    return next(u for u in USUARIOS_DE_DEMONSTRACAO if u.perfil == perfil)


def conteudo(token: str) -> dict:
    """O conteúdo do token, sem conferir a assinatura: quem confere é o serviço que o recebe."""
    return jwt.decode(token, options={"verify_signature": False})


def destinatarios(conteudo_do_token: dict) -> list[str]:
    """O `aud` como lista: o provedor o escreve como texto quando há um só."""
    aud = conteudo_do_token.get("aud", [])
    return [aud] if isinstance(aud, str) else aud


def senha_de(nome_de_usuario: str) -> str:
    return next(u for u in USUARIOS_DE_DEMONSTRACAO if u.nome_de_usuario == nome_de_usuario).senha()


def aplicacao(identificador: str = APLICACAO_WEB) -> Aplicacao:
    """Um cliente do realm que faz login; por padrão, a aplicação `pulso-web`."""
    return aplicacoes(variavel("ENDERECO_DO_FRONTEND"))[identificador]


def _pedir_token(dados: dict[str, str], emissor_do_realm: str | None = None) -> str:
    """Pede um token de acesso ao endpoint de token de um realm; por padrão, o da aplicação."""
    return fluxo_de_codigo.pedir_tokens(emissor_do_realm or emissor(), dados)["access_token"]


def tela_de_login() -> str:
    """O HTML da tela de login, como o navegador o recebe ao entrar na aplicação."""
    with httpx.Client(timeout=10) as navegador:
        return fluxo_de_codigo.abrir_tela_de_login(
            navegador, emissor(), aplicacao(), secrets.token_urlsafe(43)
        ).text


def tela_apos_credenciais(
    nome_de_usuario: str, senha: str, navegador: httpx.Client | None = None
) -> str:
    """O HTML que o provedor devolve depois de um envio de credenciais que não entra.

    Passe um `navegador` para enviar várias tentativas pela mesma conexão, em sequência rápida.
    """
    if navegador is None:
        with httpx.Client(timeout=10) as novo:
            return tela_apos_credenciais(nome_de_usuario, senha, novo)
    resposta = fluxo_de_codigo.enviar_credenciais(
        navegador, emissor(), aplicacao(), secrets.token_urlsafe(43), nome_de_usuario, senha
    )
    assert resposta.status_code == 200, "o provedor aceitou as credenciais"
    return resposta.text


def token_pelo_fluxo_de_codigo(
    nome_de_usuario: str, senha: str, identificador: str = APLICACAO_WEB
) -> str:
    """Faz login como um navegador, pelo fluxo de código com PKCE, e devolve o token de acesso.

    Por padrão o login é o da aplicação `pulso-web`; `identificador` escolhe outro cliente.
    """
    return tokens_pelo_fluxo_de_codigo(nome_de_usuario, senha, identificador)["access_token"]


def tokens_pelo_fluxo_de_codigo(
    nome_de_usuario: str, senha: str, identificador: str = APLICACAO_WEB
) -> dict[str, str]:
    """O mesmo login, devolvendo a resposta inteira do provedor: token de acesso, de id e outros."""
    return fluxo_de_codigo.tokens_pelo_fluxo_de_codigo(
        emissor(), aplicacao(identificador), nome_de_usuario, senha
    )


def token_de_outro_servico(nome_de_usuario: str, senha: str) -> str:
    """Um token do mesmo provedor e do mesmo usuário, mas emitido para outro serviço.

    O `admin-cli` existe em todo realm, aceita senha direto e não traz a API entre os
    destinatários. É a exceção ao fluxo de código: um token realista de "mesmo provedor, outro
    serviço" que não depende de cliente nenhum declarado no realm versionado.
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
