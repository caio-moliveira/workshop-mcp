"""Executa a carga: derruba o banco, recria e aplica a estrutura em ordem.

A recarga é esta mesma execução, para que "subir do zero" e "voltar ao
estado inicial" nunca divirjam (ADR 0001).
"""

import random
import sys
from pathlib import Path

import psycopg
from faker import Faker
from psycopg import sql

from carga.avaliacoes import gerar_avaliacoes
from carga.calendario import Calendario
from carga.catalogo import gerar_catalogo
from carga.comercial import gerar_comercial
from carga.conexao import conectar, variavel_obrigatoria
from carga.configuracao import Configuracao, ler_configuracao
from carga.gravacao import gravar
from carga.impressao_digital import impressao_digital, imprimir
from carga.vendas import gerar_vendas

DIRETORIO_SQL = Path(__file__).resolve().parent / "sql"


# O papel de cada perfil e a variável de ambiente com a senha da sua credencial.
VARIAVEL_DA_SENHA_POR_PAPEL = {"vendas": "SENHA_DO_PAPEL_VENDAS"}


def _recriar_papeis(conexao: psycopg.Connection, banco: str) -> None:
    """Papéis existem fora do banco: a carga os derruba e recria junto com ele (ADR 0001)."""
    for papel, variavel_da_senha in VARIAVEL_DA_SENHA_POR_PAPEL.items():
        nome = sql.Identifier(papel)
        conexao.execute(sql.SQL("drop role if exists {}").format(nome))
        conexao.execute(
            sql.SQL("create role {} login password {}").format(
                nome, sql.Literal(variavel_obrigatoria(variavel_da_senha))
            )
        )
        # Defesa extra, não a garantia: a sessão começa somente leitura, mas pode pedir
        # uma transação de escrita. Quem barra a escrita são os privilégios.
        conexao.execute(
            sql.SQL("alter role {} set default_transaction_read_only = on").format(nome)
        )
        conexao.execute(
            sql.SQL("grant connect on database {} to {}").format(sql.Identifier(banco), nome)
        )


def _restringir_outros_bancos_do_servidor(conexao: psycopg.Connection, banco: str) -> None:
    """Os outros bancos do servidor (postgres, templates, o banco padrão do usuário) não
    aceitam conexão, tabela temporária nem criação de objetos por permissão padrão."""
    outros = conexao.execute(
        "select datname from pg_database where datname <> %s order by datname", (banco,)
    ).fetchall()
    for (outro,) in outros:
        conexao.execute(
            sql.SQL("revoke all on database {} from public").format(sql.Identifier(outro))
        )


def _recriar_banco(banco: str) -> None:
    with conectar("postgres", autocommit=True) as conexao:
        nome = sql.Identifier(banco)
        conexao.execute(sql.SQL("drop database if exists {} with (force)").format(nome))
        conexao.execute(sql.SQL("create database {}").format(nome))
        # Datas e momentos de compra são lidos no fuso de Brasília, como no negócio.
        conexao.execute(
            sql.SQL("alter database {} set timezone to 'America/Sao_Paulo'").format(nome)
        )
        # Ninguém conecta, cria objetos ou tabelas temporárias sem permissão explícita.
        conexao.execute(sql.SQL("revoke all on database {} from public").format(nome))
        _restringir_outros_bancos_do_servidor(conexao, banco)
        _recriar_papeis(conexao, banco)


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

    avaliacoes = gerar_avaliacoes(rng, vendas, configuracao.data_referencia)
    gravar(conexao, "avaliacao", avaliacoes)


def _carregar(banco: str, configuracao: Configuracao) -> None:
    """Estrutura e dados entram em uma única transação: ou tudo, ou nada."""
    with conectar(banco) as conexao:
        _aplicar_estrutura(conexao)
        print(
            f"carga: gerando dados com semente {configuracao.semente}"
            f" e data de referência {configuracao.data_referencia}"
        )
        _gerar_dados(conexao, configuracao)
        # Estatísticas prontas: sem elas, as primeiras consultas após a carga são lentas.
        conexao.execute("analyze")
        impressao = impressao_digital(conexao)
    # Só imprime depois do commit, para a impressão digital corresponder ao banco gravado.
    imprimir(impressao)


def main() -> int:
    banco = variavel_obrigatoria("BANCO")
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
