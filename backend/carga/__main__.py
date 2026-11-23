"""Executa a carga: derruba o banco, recria e aplica a estrutura em ordem.

A recarga é esta mesma execução, para que "subir do zero" e "voltar ao
estado inicial" nunca divirjam (ADR 0001).
"""

import os
import random
import sys
from pathlib import Path

import psycopg
from faker import Faker
from psycopg import sql

from carga.calendario import Calendario
from carga.catalogo import gerar_catalogo
from carga.comercial import gerar_comercial
from carga.configuracao import Configuracao, ler_configuracao
from carga.gravacao import gravar
from carga.impressao_digital import impressao_digital
from carga.vendas import gerar_vendas

DIRETORIO_SQL = Path(__file__).resolve().parent / "sql"


def _variavel(nome: str) -> str:
    valor = os.environ.get(nome)
    if not valor:
        raise SystemExit(f"carga: variável de ambiente {nome} ausente")
    return valor


def _conectar(banco: str, *, autocommit: bool = False) -> psycopg.Connection:
    return psycopg.connect(
        host=_variavel("POSTGRES_HOST"),
        port=int(os.environ.get("POSTGRES_INTERNAL_PORT", "5432")),
        user=_variavel("POSTGRES_USER"),
        password=_variavel("POSTGRES_PASSWORD"),
        dbname=banco,
        connect_timeout=10,
        autocommit=autocommit,
    )


def _recriar_banco(banco: str) -> None:
    with _conectar("postgres", autocommit=True) as conexao:
        nome = sql.Identifier(banco)
        conexao.execute(sql.SQL("drop database if exists {} with (force)").format(nome))
        conexao.execute(sql.SQL("create database {}").format(nome))
        # Datas e momentos de compra são lidos no fuso de Brasília, como no negócio.
        conexao.execute(
            sql.SQL("alter database {} set timezone to 'America/Sao_Paulo'").format(nome)
        )


def _aplicar_estrutura(conexao: psycopg.Connection) -> None:
    for arquivo in sorted(DIRETORIO_SQL.glob("*.sql")):
        print(f"carga: aplicando {arquivo.name}")
        conexao.execute(arquivo.read_text(encoding="utf-8"))


def _gerar_dados(conexao: psycopg.Connection, configuracao: Configuracao) -> None:
    rng = random.Random(configuracao.semente)
    fake = Faker("pt_BR")
    fake.seed_instance(configuracao.semente)
    calendario = Calendario(configuracao.data_referencia)

    comercial = gerar_comercial(rng, fake, calendario)
    gravar(conexao, "lojista", comercial.lojistas)
    gravar(conexao, "lead", comercial.leads)

    catalogo = gerar_catalogo(rng, comercial.lojistas)
    gravar(conexao, "categoria", catalogo.categorias)
    gravar(conexao, "produto", catalogo.produtos)

    vendas = gerar_vendas(rng, fake, calendario, comercial, catalogo)
    gravar(conexao, "cliente", vendas.clientes)
    gravar(conexao, "pedido", vendas.pedidos)
    gravar(conexao, "item_pedido", vendas.itens)
    gravar(conexao, "pagamento", vendas.pagamentos)
    gravar(conexao, "entrega", vendas.entregas)


def _carregar(banco: str, configuracao: Configuracao) -> None:
    """Estrutura e dados entram em uma única transação: ou tudo, ou nada."""
    with _conectar(banco) as conexao:
        _aplicar_estrutura(conexao)
        print(
            f"carga: gerando dados com semente {configuracao.semente}"
            f" e data de referência {configuracao.data_referencia}"
        )
        _gerar_dados(conexao, configuracao)
        impressao = impressao_digital(conexao)
    # Só imprime depois do commit, para a impressão digital corresponder ao banco gravado.
    for tabela, valor in impressao.items():
        print(f"carga: impressão digital {tabela} {valor}")


def main() -> int:
    banco = _variavel("BANCO")
    configuracao = ler_configuracao()
    try:
        print(f"carga: recriando o banco {banco}")
        _recriar_banco(banco)
        _carregar(banco, configuracao)
    except psycopg.Error as erro:
        print(f"carga: falhou: {erro}", file=sys.stderr)
        return 1
    print("carga: concluída")
    return 0


if __name__ == "__main__":
    sys.exit(main())
