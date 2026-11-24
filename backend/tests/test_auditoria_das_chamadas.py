"""A auditoria das chamadas ao servidor MCP do ambiente (RF-30, ADR 0008).

Um cliente MCP faz a chamada como um assistente faria, e o teste confere a linha da auditoria,
lida com a credencial do dono, logo depois da resposta.
"""

from apoio import ultima_chamada_de, valor
from cliente_mcp import MCP_DO_AMBIENTE, chamar
from provedor import conteudo

from acesso import Perfil

# O relógio dos contêineres pode se afastar do desta máquina: o horário é comparado com o do
# Postgres, que roda ao lado do servidor MCP.
AGORA_NO_BANCO = "select clock_timestamp()"


def test_a_chamada_permitida_fica_na_auditoria_antes_da_resposta(token_de, conexao_dono):
    token = token_de(Perfil.VENDAS)
    do_token = conteudo(token)
    antes = valor(conexao_dono, AGORA_NO_BANCO)

    resultado = chamar(MCP_DO_AMBIENTE, token, "vendas_indicadores", {"periodo": "30d"})

    depois = valor(conexao_dono, AGORA_NO_BANCO)
    assert not resultado.is_error
    # Lida logo depois da resposta: a linha já precisa estar no banco.
    linha = ultima_chamada_de(do_token["sub"])
    assert linha is not None
    assert linha["nome_do_usuario"] == do_token["name"]
    assert linha["perfil"] == "vendas"
    assert linha["ferramenta"] == "vendas_indicadores"
    assert linha["parametros"] == {"periodo": "30d"}
    assert linha["parametros_cortados"] is False
    assert linha["resultado"] == "permitida"
    assert antes <= linha["horario"] <= depois
