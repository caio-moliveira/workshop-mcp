"""Os tetos da pergunta ao assistente e as falhas no meio da resposta.

Como na rota do assistente: a API é criada dentro do processo, com um modelo roteirizado, os
tetos montados pela fábrica, o token do provedor do compose e o serviço `mcp` do compose.
"""

import pytest
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil
from assistente import Limites

UM_LACO = [("vendas_indicadores", {"periodo": "30d"})] * 20


def test_o_modelo_em_laco_para_no_teto_de_chamadas_e_termina_com_fim_e_aviso(criar_api, token_de):
    api = criar_api(modelo=modelo_roteirizado(chamadas=UM_LACO), limites=Limites(chamadas=2))

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS)))

    tipo, dados = lidos[-1]
    assert tipo == "fim"
    assert dados["aviso"]
    assert [tipo for tipo, _ in lidos].count("estado") <= 3
    assert not any(tipo == "erro" for tipo, _ in lidos)
