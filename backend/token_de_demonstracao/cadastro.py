"""Quem pode pedir um token de demonstração e por qual aplicação: o espelho do realm versionado.

Os usuários de demonstração e os clientes que fazem login estão em `keycloak/realm/pulso.json`.
Um cliente novo do realm entra aqui com uma linha em `aplicacoes`.
"""

import os
from dataclasses import dataclass

from acesso import Perfil
from token_de_demonstracao.fluxo_de_codigo import Aplicacao

APLICACAO_WEB = "pulso-web"
# O login pelo MCP Inspector: o retorno é a página que o Inspector abre na máquina local, e repete o
# `redirectUris` do cliente no realm.
INSPECTOR = "pulso-inspector"
RETORNO_DO_INSPECTOR = "http://localhost:6274/oauth/callback"
# Um cliente do mesmo realm que não é a aplicação: o token dele não vale na API nem no servidor
# MCP (CA-03). Ninguém escuta no retorno: o fluxo lê o código do redirecionamento, sem segui-lo.
# O endereço repete o `redirectUris` do cliente no realm.
OUTRA_APLICACAO = "pulso-outra-aplicacao"
RETORNO_DA_OUTRA_APLICACAO = "http://localhost:8765/retorno"


class VariavelAusente(Exception):
    """Falta no ambiente uma variável obrigatória; a mensagem é o nome dela."""


def variavel(nome: str) -> str:
    """O valor de uma variável de ambiente obrigatória."""
    valor = os.environ.get(nome)
    if not valor:
        raise VariavelAusente(nome)
    return valor


@dataclass(frozen=True)
class UsuarioDeDemonstracao:
    nome_de_usuario: str
    variavel_da_senha: str
    nome: str
    perfil: Perfil

    def senha(self) -> str:
        """A senha vem sempre do ambiente: nunca de argumento, e não vai para saída nem log."""
        return variavel(self.variavel_da_senha)


USUARIOS_DE_DEMONSTRACAO = [
    UsuarioDeDemonstracao("ana.vendas", "SENHA_DO_USUARIO_VENDAS", "Ana Ribeiro", Perfil.VENDAS),
    # O segundo usuário de Vendas mostra que um usuário não vê o histórico de outro do mesmo
    # perfil (RF-08, RF-18). Fica depois da Ana: quem pede "o usuário de um perfil" recebe ela.
    UsuarioDeDemonstracao(
        "vitor.vendas", "SENHA_DO_USUARIO_VENDAS_VITOR", "Vitor Nunes", Perfil.VENDAS
    ),
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


def aplicacoes(endereco_do_frontend: str) -> dict[str, Aplicacao]:
    """Os clientes do realm que fazem login, por identificador, com o retorno de cada um."""
    conhecidas = [
        Aplicacao(APLICACAO_WEB, f"{endereco_do_frontend}/"),
        Aplicacao(INSPECTOR, RETORNO_DO_INSPECTOR),
        Aplicacao(OUTRA_APLICACAO, RETORNO_DA_OUTRA_APLICACAO),
    ]
    return {aplicacao.identificador: aplicacao for aplicacao in conhecidas}
