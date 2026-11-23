"""A tela de login do provedor tem a cara do `pulso.` e não revela quais usuários existem."""

import html
import re

from provedor import tela_apos_credenciais, tela_de_login


def _mensagem_de_erro(pagina: str) -> str:
    erro = re.search(r'id="input-error"[^>]*>(.*?)</span>', pagina, re.DOTALL)
    assert erro, "a tela não mostra mensagem de credencial inválida"
    return html.unescape(erro.group(1)).strip()


def test_o_realm_usa_o_tema_de_login_do_pulso():
    assert "/login/pulso/" in tela_de_login()


def test_usuario_inexistente_e_senha_errada_recebem_a_mesma_mensagem():
    senha_errada = _mensagem_de_erro(tela_apos_credenciais("ana.vendas", "senha-errada"))
    inexistente = _mensagem_de_erro(tela_apos_credenciais("ninguem.inexistente", "senha-errada"))

    assert senha_errada
    assert senha_errada == inexistente
