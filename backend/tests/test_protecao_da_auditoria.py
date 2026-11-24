"""A auditoria protegida contra leitura e alteração e preservada pela recarga (RF-32, ADR 0008)."""

import uuid
from dataclasses import replace

import psycopg
import pytest
from apoio import (
    BANCO_DA_AUDITORIA,
    banco_local,
    compose,
    conectar_como_auditoria,
    conectar_como_dono,
    ultima_chamada_de,
    valor,
)
from psycopg.types.json import Jsonb

from consultas import credenciais_do_ambiente

# Como o servidor MCP grava: sem `returning`, que exigiria `select`.
GRAVACAO = """
insert into auditoria.chamada (
    horario, id_do_usuario, nome_do_usuario, perfil, ferramenta, parametros,
    parametros_cortados, resultado
) values (now(), %s, 'teste.protecao', 'vendas', 'vendas_indicadores', %s, false, 'permitida')
"""


def _gravar_como_auditoria() -> str:
    """Grava uma linha com o papel `auditoria` e devolve o usuário dela, único por teste."""
    usuario = f"teste-protecao-{uuid.uuid4()}"
    with conectar_como_auditoria() as conexao:
        conexao.execute(GRAVACAO, (usuario, Jsonb({"periodo": "30d"})))
    return usuario


def test_o_papel_auditoria_insere_uma_chamada():
    usuario = _gravar_como_auditoria()

    linha = ultima_chamada_de(usuario)
    assert linha is not None
    assert linha["parametros"] == {"periodo": "30d"}


@pytest.mark.parametrize(
    "comando",
    [
        "select * from auditoria.chamada",
        "update auditoria.chamada set resultado = 'negada'",
        "delete from auditoria.chamada",
        "truncate auditoria.chamada",
    ],
)
def test_o_papel_auditoria_nao_le_nao_altera_nem_apaga(comando):
    usuario = _gravar_como_auditoria()

    with conectar_como_auditoria() as conexao, pytest.raises(psycopg.errors.InsufficientPrivilege):
        conexao.execute(comando)
    # A linha gravada continua lá, intacta.
    assert ultima_chamada_de(usuario)["resultado"] == "permitida"


def test_a_recarga_preserva_a_chamada_gravada_antes_dela():
    usuario = _gravar_como_auditoria()

    resultado = compose("run", "--rm", "carga")

    assert resultado.returncode == 0, resultado.stderr
    assert ultima_chamada_de(usuario) is not None


def test_a_recarga_so_reaplica_a_senha_do_papel_auditoria():
    # Uma senha trocada fora da carga: a recarga volta à do `.env`, sem recriar o papel.
    with conectar_como_dono(BANCO_DA_AUDITORIA) as conexao:
        conexao.execute(f"alter role auditoria password '{uuid.uuid4()}'")
        oid_antes = valor(conexao, "select oid from pg_roles where rolname = 'auditoria'")

    resultado = compose("run", "--rm", "carga")

    assert resultado.returncode == 0, resultado.stderr
    with conectar_como_dono(BANCO_DA_AUDITORIA) as conexao:
        assert valor(conexao, "select oid from pg_roles where rolname = 'auditoria'") == oid_antes
    usuario = _gravar_como_auditoria()
    assert ultima_chamada_de(usuario) is not None


# As ferramentas do servidor MCP leem o banco só pelo executor de consultas, com o papel do
# perfil, e o papel `auditoria` não lê: se nenhum papel de perfil alcança o banco da auditoria,
# nenhuma ferramenta o lê (RF-32).
@pytest.mark.parametrize("credencial", credenciais_do_ambiente().values(), ids=repr)
def test_o_papel_de_cada_perfil_nao_se_conecta_ao_banco_da_auditoria(credencial):
    banco = replace(banco_local(), nome=BANCO_DA_AUDITORIA)

    with pytest.raises(psycopg.OperationalError, match="permission denied"):
        psycopg.connect(
            host=banco.host,
            port=banco.porta,
            dbname=banco.nome,
            user=credencial.papel,
            password=credencial.senha,
            connect_timeout=5,
        ).close()
