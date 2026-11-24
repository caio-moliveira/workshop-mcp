"""Imprime o token de acesso de um usuário de demonstração, emitido para a aplicação escolhida.

Dentro de `backend/`, com o ambiente no ar:

    uv run python -m token_de_demonstracao ana.vendas pulso-outra-aplicacao

A saída padrão traz só o token, para colar no MCP Inspector ou usar em `$(...)`; qualquer mensagem
vai para a saída de erro. O endereço do provedor e a senha do usuário vêm do ambiente ou de
`backend/.env`: a senha nunca é argumento e não aparece em saída nenhuma.
"""

import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

from acesso.provedor import emissor_em
from token_de_demonstracao.cadastro import (
    USUARIOS_DE_DEMONSTRACAO,
    VariavelAusente,
    aplicacoes,
    variavel,
)
from token_de_demonstracao.fluxo_de_codigo import (
    LoginRecusado,
    TelaDeLoginInesperada,
    tokens_pelo_fluxo_de_codigo,
)

USO = "Uso: uv run python -m token_de_demonstracao <usuário> <aplicação>"
# O pedido não dá para atender como foi feito (argumentos, configuração) ou o provedor falhou.
PEDIDO_INVALIDO = 2
FALHA_NO_PROVEDOR = 1


class _Encerrar(Exception):
    """Termina o comando com uma mensagem para a saída de erro e um código de saída."""

    def __init__(self, codigo: int, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


def _token(argumentos: list[str]) -> str:
    if len(argumentos) != 2:
        raise _Encerrar(PEDIDO_INVALIDO, USO)
    nome_de_usuario, identificador = argumentos

    usuarios = {usuario.nome_de_usuario: usuario for usuario in USUARIOS_DE_DEMONSTRACAO}
    if nome_de_usuario not in usuarios:
        raise _Encerrar(
            PEDIDO_INVALIDO,
            f"Usuário de demonstração desconhecido: {nome_de_usuario}. "
            f"Os que existem: {', '.join(usuarios)}.",
        )
    try:
        conhecidas = aplicacoes(variavel("ENDERECO_DO_FRONTEND"))
        if identificador not in conhecidas:
            raise _Encerrar(
                PEDIDO_INVALIDO,
                f"Aplicação desconhecida: {identificador}. "
                f"As que existem: {', '.join(conhecidas)}.",
            )
        endereco = variavel("ENDERECO_PUBLICO_DO_PROVEDOR")
        senha = usuarios[nome_de_usuario].senha()
    except VariavelAusente as falta:
        raise _Encerrar(
            PEDIDO_INVALIDO,
            f"Variável {falta} ausente: copie backend/.env.example para backend/.env.",
        ) from None

    try:
        tokens = tokens_pelo_fluxo_de_codigo(
            emissor_em(endereco), conhecidas[identificador], nome_de_usuario, senha
        )
    except LoginRecusado:
        raise _Encerrar(
            FALHA_NO_PROVEDOR,
            f"O provedor de identidade recusou o login de {nome_de_usuario}. "
            "Confira a senha do usuário no ambiente e se a conta não está bloqueada.",
        ) from None
    except (httpx.HTTPError, TelaDeLoginInesperada) as erro:
        # Só o tipo do erro: a mensagem de um erro HTTP pode trazer a URL do pedido.
        raise _Encerrar(
            FALHA_NO_PROVEDOR,
            f"Não foi possível falar com o provedor de identidade em {endereco} "
            f"({type(erro).__name__}). O ambiente está no ar, com o realm atual?",
        ) from None
    return tokens["access_token"]


def main(argumentos: list[str]) -> int:
    # Acentos legíveis também quando a saída de erro passa por um pipe no Windows.
    sys.stderr.reconfigure(encoding="utf-8")
    # O que já está no ambiente vale mais que o arquivo.
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    try:
        token = _token(argumentos)
    except _Encerrar as fim:
        print(fim, file=sys.stderr)
        return fim.codigo
    print(token)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
