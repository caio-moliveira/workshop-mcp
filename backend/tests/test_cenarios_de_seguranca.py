"""A lista de cenários da execução de aceite, sem ambiente: o esperado bate com os registros de
donos, os grupos previstos estão cobertos e os identificadores são únicos."""

from execucao_de_aceite import cenarios
from registros import DONO_DA_ROTA

from aceite import CAMADAS_DE_DEFESA, GRUPOS

# Os grupos da matriz que já têm cenários. Cada entrega de cenários acrescenta os seus aqui.
GRUPOS_COBERTOS = {"api"}

# O esperado de cada cenário da API, escrito à parte do registro: o dono lê, os outros não.
ESPERADO_DA_API = {
    "api-dono-le-a-propria-rota": "permitido",
    "api-vendas-le-rota-da-diretoria": "negado",
    "api-produtos-le-rota-do-comercial": "negado",
    "api-periodo-invalido-em-rota-alheia": "negado",
    "api-conversa-de-outro-usuario": "negado",
}


def test_os_identificadores_sao_unicos():
    ids = [c.id for c in cenarios()]
    assert len(ids) == len(set(ids))


def test_os_grupos_previstos_estao_cobertos():
    assert {c.grupo for c in cenarios()} == GRUPOS_COBERTOS


def test_os_cenarios_seguem_a_ordem_das_camadas_de_defesa():
    ordem = [GRUPOS.index(c.grupo) for c in cenarios()]
    assert ordem == sorted(ordem)


def test_cada_cenario_declara_camadas_de_defesa_conhecidas():
    for cenario in cenarios():
        assert cenario.camadas_de_defesa, cenario.id
        assert set(cenario.camadas_de_defesa) <= set(CAMADAS_DE_DEFESA), cenario.id
        # O grupo é a camada que barra; o do assistente é barrado na Chamada.
        barra = "chamada" if cenario.grupo == "assistente" else cenario.grupo
        assert barra in cenario.camadas_de_defesa, cenario.id


def test_o_esperado_de_cada_cenario_de_rota_vem_do_registro_de_donos():
    de_rota = [c for c in cenarios() if c.alvo.tipo == "rota"]
    assert de_rota
    for cenario in de_rota:
        assert cenario.alvo.nome in DONO_DA_ROTA, cenario.id
        so_o_dono = DONO_DA_ROTA[cenario.alvo.nome] is cenario.perfil
        assert cenario.esperado == ("permitido" if so_o_dono else "negado"), cenario.id


def test_os_cenarios_da_api_sao_os_previstos():
    da_api = {c.id: c.esperado for c in cenarios() if c.grupo == "api"}
    assert da_api == ESPERADO_DA_API


def test_os_dois_perfis_negados_na_rota_alheia_sao_de_perfis_diferentes():
    """`ana.vendas` numa rota da Diretoria e `bruno.produtos` numa do Comercial: o mesmo 403."""
    por_id = {c.id: c for c in cenarios()}
    vendas = por_id["api-vendas-le-rota-da-diretoria"]
    produtos = por_id["api-produtos-le-rota-do-comercial"]
    assert (vendas.quem.nome, produtos.quem.nome) == ("ana.vendas", "bruno.produtos")
    assert DONO_DA_ROTA[vendas.alvo.nome] != DONO_DA_ROTA[produtos.alvo.nome]
