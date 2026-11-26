"""A lista de cenários da execução de aceite, sem ambiente: o esperado bate com os registros de
donos, os grupos previstos estão cobertos e os identificadores são únicos."""

from execucao_de_aceite import cenarios
from registros import DONO_DA_FERRAMENTA, DONO_DA_ROTA

from aceite import CAMADAS_DE_DEFESA, GRUPOS

# Os grupos da matriz que já têm cenários. Cada entrega de cenários acrescenta os seus aqui.
GRUPOS_COBERTOS = {"api"}
GRUPOS_COBERTOS |= {"banco", "limite_de_frequencia", "assistente"}

# O esperado de cada cenário do Banco, escrito à parte: cada papel lê só a própria camada de
# leitura, nenhum lê os dados de origem e nenhum escreve (ADR 0002).
ESPERADO_DO_BANCO = {
    "banco-vendas-le-a-propria-camada": ("vendas", "vendas.pedido", "permitido"),
    "banco-vendas-le-a-camada-da-diretoria": ("vendas", "diretoria.indicadores", "negado"),
    "banco-diretoria-le-os-dados-de-origem": ("diretoria", "dados_de_origem.pedido", "negado"),
    "banco-comercial-escreve-na-propria-camada": ("comercial", "comercial.lead", "negado"),
}

# O Vitor passa do limite e é barrado; a Ana, logo depois, continua passando (RS-11).
ESPERADO_DO_LIMITE = [
    ("limite-vitor-passa-do-limite", "vitor.vendas", "negado"),
    ("limite-ana-continua-passando", "ana.vendas", "permitido"),
]

# O assistente, com o modelo roteirizado: a própria ferramenta é permitida e a de outro perfil é
# negada na chamada.
ESPERADO_DO_ASSISTENTE = {
    "assistente-chama-o-mcp-com-o-token-do-usuario": "permitido",
    "assistente-ferramenta-de-outro-perfil": "negado",
}

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


def test_toda_camada_de_defesa_dos_grupos_cobertos_barra_algum_cenario():
    """Com todos os grupos cobertos, as seis camadas de defesa e o grupo do assistente estão."""
    camadas = {camada for c in cenarios() for camada in c.camadas_de_defesa}
    assert GRUPOS_COBERTOS - {"assistente"} <= camadas
    assert set(camadas) <= set(CAMADAS_DE_DEFESA)


def test_os_cenarios_do_banco_sao_os_previstos():
    do_banco = {
        c.id: (c.quem.nome, c.alvo.nome, c.esperado) for c in cenarios() if c.grupo == "banco"
    }
    assert do_banco == ESPERADO_DO_BANCO
    for cenario in cenarios():
        if cenario.grupo == "banco":
            assert cenario.quem.tipo == "papel", cenario.id
            assert cenario.camadas_de_defesa == ("banco",), cenario.id


def test_o_cenario_do_limite_usa_o_vitor_e_depois_a_ana_e_exige_o_limite_padrao():
    do_limite = [c for c in cenarios() if c.grupo == "limite_de_frequencia"]
    assert [(c.id, c.quem.nome, c.esperado) for c in do_limite] == ESPERADO_DO_LIMITE
    assert all(c.exige_limite_padrao for c in do_limite)
    # Só o limite exige o servidor MCP no limite padrão.
    assert not [c.id for c in cenarios() if c.exige_limite_padrao and c not in do_limite]


def test_os_cenarios_do_assistente_tem_o_esperado_dos_registros_de_donos():
    do_assistente = [c for c in cenarios() if c.grupo == "assistente"]
    assert {c.id: c.esperado for c in do_assistente} == ESPERADO_DO_ASSISTENTE
    for cenario in do_assistente:
        assert cenario.alvo.tipo == "assistente", cenario.id
        ferramenta = cenario.alvo.parametros["ferramenta"]
        so_o_dono = DONO_DA_FERRAMENTA[ferramenta] is cenario.perfil
        assert cenario.esperado == ("permitido" if so_o_dono else "negado"), cenario.id


def test_os_dois_perfis_negados_na_rota_alheia_sao_de_perfis_diferentes():
    """`ana.vendas` numa rota da Diretoria e `bruno.produtos` numa do Comercial: o mesmo 403."""
    por_id = {c.id: c for c in cenarios()}
    vendas = por_id["api-vendas-le-rota-da-diretoria"]
    produtos = por_id["api-produtos-le-rota-do-comercial"]
    assert (vendas.quem.nome, produtos.quem.nome) == ("ana.vendas", "bruno.produtos")
    assert DONO_DA_ROTA[vendas.alvo.nome] != DONO_DA_ROTA[produtos.alvo.nome]
