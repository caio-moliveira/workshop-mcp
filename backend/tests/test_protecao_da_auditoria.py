"""A auditoria protegida contra leitura e alteração e preservada pela recarga (RF-32, ADR 0008)."""

import uuid

import psycopg
import pytest
from apoio import conectar_como_auditoria, ultima_chamada_de
from psycopg.types.json import Jsonb

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
