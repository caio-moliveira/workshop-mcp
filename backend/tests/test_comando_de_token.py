"""O comando de token de demonstração, rodado como o apresentador o roda.

`python -m token_de_demonstracao <usuário> <aplicação>` dentro de `backend/`: imprime só o token
de acesso, para colar no MCP Inspector ou usar em `$(...)`. Qualquer mensagem vai para a saída de
erro, e as senhas vêm do ambiente.
"""

import os
import subprocess
import sys

import jwt
import pytest
from apoio import BACKEND
from provedor import USUARIOS_DE_DEMONSTRACAO

VARIAVEIS_DE_SENHA = [usuario.variavel_da_senha for usuario in USUARIOS_DE_DEMONSTRACAO]
USO = "Uso: uv run python -m token_de_demonstracao <usuário> <aplicação>"


def _rodar(*argumentos: str, ambiente: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, "-m", "token_de_demonstracao", *argumentos],
        cwd=BACKEND,
        env=ambiente,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _sem_rastro_de_pilha_nem_senha(resultado) -> None:
    saidas = resultado.stdout + resultado.stderr
    assert "Traceback" not in saidas
    assert not any(usuario.senha() in saidas for usuario in USUARIOS_DE_DEMONSTRACAO)


@pytest.mark.parametrize(
    ("aplicacao", "destinatarios"),
    [
        ("pulso-web", ["pulso-api", "pulso-mcp"]),
        ("pulso-outra-aplicacao", ["pulso-outra-aplicacao"]),
    ],
)
def test_imprime_so_o_token_de_acesso_do_usuario_pela_aplicacao(aplicacao, destinatarios):
    resultado = _rodar("ana.vendas", aplicacao)

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stderr == ""
    assert resultado.stdout.endswith("\n")
    token = resultado.stdout.removesuffix("\n")
    conteudo = jwt.decode(token, options={"verify_signature": False})
    assert conteudo["preferred_username"] == "ana.vendas"
    assert conteudo["perfil"] == "vendas"
    assert conteudo["azp"] == aplicacao
    recebidos = conteudo["aud"]
    assert sorted([recebidos] if isinstance(recebidos, str) else recebidos) == destinatarios
    _sem_rastro_de_pilha_nem_senha(resultado)


def test_le_as_senhas_do_arquivo_de_ambiente_quando_o_shell_nao_as_tem():
    """O apresentador não exporta nada: o comando lê `backend/.env`, como o compose."""
    do_arquivo = {*VARIAVEIS_DE_SENHA, "ENDERECO_PUBLICO_DO_PROVEDOR", "ENDERECO_DO_FRONTEND"}
    ambiente = {nome: valor for nome, valor in os.environ.items() if nome not in do_arquivo}

    resultado = _rodar("bruno.produtos", "pulso-web", ambiente=ambiente)

    assert resultado.returncode == 0, resultado.stderr
    conteudo = jwt.decode(resultado.stdout.strip(), options={"verify_signature": False})
    assert conteudo["perfil"] == "produtos"


@pytest.mark.parametrize(
    ("argumentos", "mensagem"),
    [
        (
            ("fulano.inexistente", "pulso-web"),
            "Usuário de demonstração desconhecido: fulano.inexistente.",
        ),
        (("ana.vendas", "pulso-que-nao-existe"), "Aplicação desconhecida: pulso-que-nao-existe."),
        (("ana.vendas",), USO),
        ((), USO),
    ],
    ids=["usuario", "aplicacao", "falta-a-aplicacao", "sem-argumentos"],
)
def test_pedido_que_nao_da_para_atender_termina_com_erro_claro(argumentos, mensagem):
    resultado = _rodar(*argumentos)

    assert resultado.returncode == 2
    assert resultado.stdout == ""
    assert resultado.stderr.startswith(mensagem)
    _sem_rastro_de_pilha_nem_senha(resultado)


def test_o_erro_de_usuario_ou_aplicacao_desconhecidos_diz_quais_existem():
    assert "ana.vendas, bruno.produtos, carla.comercial, diego.diretoria" in (
        _rodar("fulano.inexistente", "pulso-web").stderr
    )
    assert "pulso-web, pulso-outra-aplicacao" in _rodar("ana.vendas", "pulso-x").stderr


def test_senha_recusada_pelo_provedor_termina_com_erro_claro():
    ambiente = os.environ | {"SENHA_DO_USUARIO_VENDAS": "senha-que-nao-e-a-da-ana"}

    resultado = _rodar("ana.vendas", "pulso-web", ambiente=ambiente)

    assert resultado.returncode == 1
    assert resultado.stdout == ""
    assert resultado.stderr.startswith("O provedor de identidade recusou o login de ana.vendas.")
    assert "senha-que-nao-e-a-da-ana" not in resultado.stderr
    assert "Traceback" not in resultado.stderr


def test_provedor_fora_do_ar_termina_com_erro_claro():
    ambiente = os.environ | {"ENDERECO_PUBLICO_DO_PROVEDOR": "http://127.0.0.1:9"}

    resultado = _rodar("ana.vendas", "pulso-web", ambiente=ambiente)

    assert resultado.returncode == 1
    assert resultado.stdout == ""
    assert resultado.stderr.startswith("Não foi possível falar com o provedor de identidade")
    _sem_rastro_de_pilha_nem_senha(resultado)
