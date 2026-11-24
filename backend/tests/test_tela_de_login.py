"""A tela de login do provedor tem a cara do `pulso.` e não revela quais usuários existem."""

import html
import re
import secrets
from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import pytest
from provedor import administracao, tela_apos_credenciais, tela_de_login

MENSAGEM_DE_CREDENCIAL_INVALIDA = "Usuário ou senha inválidos."


def _mensagem_de_erro(pagina: str) -> str:
    erro = re.search(r'id="input-error"[^>]*>(.*?)</span>', pagina, re.DOTALL)
    assert erro, "a tela não mostra mensagem de credencial inválida"
    return html.unescape(erro.group(1)).strip()


@dataclass(frozen=True)
class UsuarioDescartavel:
    nome_de_usuario: str
    senha: str
    identificador: str
    admin: httpx.Client

    def bloqueado(self) -> bool:
        """Se o provedor bloqueou a conta por excesso de tentativas erradas."""
        estado = self.admin.get(f"/attack-detection/brute-force/users/{self.identificador}")
        estado.raise_for_status()
        return estado.json()["disabled"]


@pytest.fixture
def usuario_descartavel() -> Iterator[UsuarioDescartavel]:
    """Um usuário criado só para o teste e apagado no fim. Os de demonstração ficam intactos."""
    nome_de_usuario = f"descartavel.{secrets.token_hex(4)}"
    senha = secrets.token_urlsafe(16)
    with administracao() as admin:
        criacao = admin.post(
            "/users",
            json={
                "username": nome_de_usuario,
                "enabled": True,
                "credentials": [{"type": "password", "value": senha, "temporary": False}],
            },
        )
        assert criacao.status_code == 201, criacao.text
        identificador = criacao.headers["location"].rsplit("/", 1)[-1]
        try:
            yield UsuarioDescartavel(nome_de_usuario, senha, identificador, admin)
        finally:
            admin.delete(f"/users/{identificador}")


def test_o_realm_usa_o_tema_de_login_do_pulso():
    assert "/login/pulso/" in tela_de_login()


def test_usuario_inexistente_e_senha_errada_recebem_a_mesma_mensagem():
    senha_errada = _mensagem_de_erro(tela_apos_credenciais("ana.vendas", "senha-errada"))
    inexistente = _mensagem_de_erro(tela_apos_credenciais("ninguem.inexistente", "senha-errada"))

    assert senha_errada == MENSAGEM_DE_CREDENCIAL_INVALIDA
    assert inexistente == MENSAGEM_DE_CREDENCIAL_INVALIDA


def test_conta_bloqueada_por_tentativas_recebe_a_mesma_mensagem(usuario_descartavel):
    """O bloqueio por força bruta não pode revelar que o usuário existe."""
    usuario = usuario_descartavel
    # Quantas tentativas erradas bastam depende da política do realm: erra até bloquear, pela
    # mesma conexão, como alguém tentando adivinhar a senha.
    with httpx.Client(timeout=10) as navegador:
        for _ in range(40):
            tela_apos_credenciais(usuario.nome_de_usuario, "senha-errada", navegador)
            if usuario.bloqueado():
                break
    assert usuario.bloqueado(), "o provedor não bloqueou a conta"

    # Bloqueada, a conta recusa até a senha certa, e com a mesma mensagem de sempre.
    pagina = tela_apos_credenciais(usuario.nome_de_usuario, usuario.senha)

    assert _mensagem_de_erro(pagina) == MENSAGEM_DE_CREDENCIAL_INVALIDA
