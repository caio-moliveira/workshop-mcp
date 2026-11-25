"""O banco do histórico: criado pela carga e preservado pela recarga (RF-18, ADR 0009)."""

import uuid

import psycopg
import pytest
from apoio import (
    BANCO_DA_AUDITORIA,
    BANCO_DO_HISTORICO,
    compose,
    conectar_como_auditoria,
    conectar_como_dono,
    conectar_como_historico,
    conectar_como_vendas,
    variavel,
)


def _gravar_conversa_como_dono() -> uuid.UUID:
    """Uma conversa gravada direto no banco, só para ver se a recarga a preserva."""
    identificador = uuid.uuid4()
    with conectar_como_dono(BANCO_DO_HISTORICO) as conexao:
        conexao.execute(
            "insert into historico.conversa (id, id_do_usuario, perfil, titulo, ultima_atividade)"
            " values (%s, 'teste-recarga', 'vendas', 'Antes da recarga', now())",
            (identificador,),
        )
    return identificador


def _existe(identificador: uuid.UUID) -> bool:
    with conectar_como_dono(BANCO_DO_HISTORICO) as conexao:
        return (
            conexao.execute(
                "select 1 from historico.conversa where id = %s", (identificador,)
            ).fetchone()
            is not None
        )


def test_a_recarga_preserva_a_conversa_gravada_antes_dela():
    identificador = _gravar_conversa_como_dono()

    resultado = compose("run", "--rm", "carga")

    assert resultado.returncode == 0, resultado.stderr
    assert _existe(identificador)


# O papel do histórico só alcança o banco dele, e nenhum outro papel o alcança: nem o de perfil,
# que as ferramentas usam, nem o da auditoria, que o servidor MCP usa (ADR 0009).


@pytest.mark.parametrize("banco", [variavel("BANCO"), BANCO_DA_AUDITORIA])
def test_o_papel_do_historico_nao_se_conecta_aos_outros_bancos(banco):
    with pytest.raises(psycopg.OperationalError, match="permission denied"):
        conectar_como_historico(banco).close()


@pytest.mark.parametrize("conectar", [conectar_como_vendas, conectar_como_auditoria])
def test_os_outros_papeis_nao_se_conectam_ao_banco_do_historico(conectar):
    with pytest.raises(psycopg.OperationalError, match="permission denied"):
        conectar(BANCO_DO_HISTORICO).close()
