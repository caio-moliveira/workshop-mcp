"""O rastreio da resposta: as chamadas que a produziram, no fluxo e na conversa gravada (FE §8).

A API é criada dentro do processo, com um modelo roteirizado. O resto é de verdade: o token do
provedor do compose, o serviço `mcp` do compose e o banco `historico` do compose.
"""

import pytest
from cliente_mcp import PARAMETRO_INVALIDO
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil

FERRAMENTA_DE_VENDAS = "vendas_indicadores"
FERRAMENTA_INVENTADA = "exportar_tudo"
# O que cada evento `chamada` traz, e nada além: nem parâmetro nem texto de erro (FE §8).
CAMPOS_DA_CHAMADA = {"ferramenta", "desfecho", "milissegundos"}


def _chamadas(lidos) -> list[dict]:
    return [dados for tipo, dados in lidos if tipo == "chamada"]


def test_chamada_de_vendas_sai_como_concluida_com_a_duracao(criar_api, token_de):
    api = criar_api(
        modelo=modelo_roteirizado(chamadas=[(FERRAMENTA_DE_VENDAS, {"periodo": "30d"})])
    )

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS)))

    [chamada] = _chamadas(lidos)
    assert set(chamada) == CAMPOS_DA_CHAMADA
    assert chamada["ferramenta"] == FERRAMENTA_DE_VENDAS
    assert chamada["desfecho"] == "concluida"
    assert isinstance(chamada["milissegundos"], int)
    assert chamada["milissegundos"] >= 0
    # A chamada termina antes do texto da resposta que a usa.
    tipos = [tipo for tipo, _ in lidos]
    assert tipos.index("chamada") < tipos.index("texto")


@pytest.mark.parametrize(
    ("perfil", "ferramenta"),
    [(Perfil.PRODUTOS, FERRAMENTA_DE_VENDAS), (Perfil.VENDAS, FERRAMENTA_INVENTADA)],
    ids=["de-outro-perfil", "inventada"],
)
def test_chamada_negada_sai_como_nao_concluida_com_o_nome_pedido(
    criar_api, token_de, perfil, ferramenta
):
    api = criar_api(modelo=modelo_roteirizado(chamadas=[(ferramenta, {"periodo": "30d"})]))

    lidos = eventos(perguntar(api, token_de(perfil)))

    [chamada] = _chamadas(lidos)
    assert chamada["ferramenta"] == ferramenta
    assert chamada["desfecho"] == "nao_concluida"


def test_nenhum_evento_traz_parametro_nem_texto_de_erro(criar_api, token_de):
    # Um parâmetro fora da enumeração: o servidor responde com erro de ferramenta.
    parametro = "periodo-que-nao-existe"
    api = criar_api(
        modelo=modelo_roteirizado(chamadas=[(FERRAMENTA_DE_VENDAS, {"periodo": parametro})])
    )

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS)))

    [chamada] = _chamadas(lidos)
    assert chamada["desfecho"] == "nao_concluida"
    assert set(chamada) == CAMPOS_DA_CHAMADA
    assert parametro not in str(lidos)
    assert PARAMETRO_INVALIDO not in str(lidos)


def test_a_conversa_lida_depois_traz_o_rastreio_e_a_pergunta_de_cada_resposta(criar_api, token_de):
    token = token_de(Perfil.VENDAS)
    chamadas = [(FERRAMENTA_DE_VENDAS, {"periodo": "30d"}), (FERRAMENTA_INVENTADA, {})]
    api = criar_api(modelo=modelo_roteirizado(chamadas=chamadas))
    lidos = eventos(perguntar(api, token))
    _, inicio = lidos[0]
    sem_chamada = criar_api(modelo=modelo_roteirizado())
    corpo = {"pergunta": "E sem consultar nada?", "id_da_conversa": inicio["id_da_conversa"]}
    segunda = eventos(perguntar(sem_chamada, token, corpo))

    conversa = api.get(
        f"/conversas/{inicio['id_da_conversa']}", headers={"Authorization": f"Bearer {token}"}
    ).json()

    respostas = [item for item in conversa["itens"] if item["autor"] == "assistente"]
    # O rastreio gravado é o mesmo que saiu no fluxo, em ordem, com a duração medida então.
    assert respostas[0]["rastreio"] == _chamadas(lidos)
    assert [c["desfecho"] for c in respostas[0]["rastreio"]] == ["concluida", "nao_concluida"]
    assert respostas[0]["id_da_pergunta"] == inicio["id_da_pergunta"]
    # Sem chamadas, o rastreio vem vazio, e não ausente: a tela diz que nada foi consultado.
    assert respostas[1]["rastreio"] == []
    assert respostas[1]["id_da_pergunta"] == segunda[0][1]["id_da_pergunta"]
