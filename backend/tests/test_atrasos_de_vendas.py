"""A ferramenta `vendas_atrasos`: onde o atraso se concentra, por rota ou por lojista.

O servidor MCP é criado pela fábrica, dentro do processo, e lê o banco carregado; o token é
assinado por uma chave local. Os valores esperados vêm de uma leitura independente, feita com o
papel dono nos dados de origem e agrupada aqui, em Python, com os dias no horário de Brasília. O
banco é o da carga padrão (data de referência 30/11/2026).
"""

import json
from collections import Counter
from datetime import date

import pytest
from chaves_locais import ChavesLocais, assinar, conteudo_valido, nova_chave
from cliente_mcp import (
    FERRAMENTA_DESCONHECIDA,
    PARAMETRO_INVALIDO,
    chamar,
    chamar_pelo_protocolo,
    listar_ferramentas,
    texto_do_erro,
)
from provedor import DESTINATARIO_DO_MCP
from starlette.testclient import TestClient

from acesso import Perfil

CHAVE = nova_chave()
FERRAMENTA = "vendas_atrasos"
OUTROS_PERFIS = [perfil for perfil in Perfil if perfil is not Perfil.VENDAS]

PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}
AGRUPAMENTOS = ["rota", "lojista"]
LIMITE = 10

# Cada pedido do período com entrega: o lojista, as duas pontas da rota e a situação da entrega.
_NA_ORIGEM = """
select l.nome, l.uf, c.uf, e.situacao
from dados_de_origem.pedido p
join dados_de_origem.lojista l on l.id = p.lojista_id
join dados_de_origem.cliente c on c.id = p.cliente_id
join dados_de_origem.entrega e on e.pedido_id = p.id
where (p.momento_compra at time zone 'America/Sao_Paulo')::date between %s and %s
"""


def _token_de(perfil: Perfil) -> str:
    return assinar(conteudo_valido(aud=DESTINATARIO_DO_MCP, perfil=perfil.value), CHAVE)


def _esperado(conexao, agrupamento: str, periodo: str) -> dict:
    """A resposta inteira, contada aqui a partir dos dados de origem."""
    inicio, fim = PERIODOS[periodo]
    entregues, atrasos = Counter(), Counter()
    for lojista, uf_do_lojista, uf_do_cliente, situacao in conexao.execute(
        _NA_ORIGEM, (inicio, fim)
    ):
        if situacao not in ("Entregue no prazo", "Entregue com atraso"):
            continue
        grupo = f"{uf_do_lojista} → {uf_do_cliente}" if agrupamento == "rota" else lojista
        entregues[grupo] += 1
        atrasos[grupo] += situacao == "Entregue com atraso"

    total_de_entregues = sum(entregues.values())
    total_de_atrasos = sum(atrasos.values())
    # Do maior número de atrasos para o menor; no empate, pelo nome do grupo.
    com_atraso = sorted(
        (grupo for grupo in entregues if atrasos[grupo]),
        key=lambda grupo: (-atrasos[grupo], grupo),
    )
    return {
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "agrupamento": agrupamento,
        "total": {
            "entregues": total_de_entregues,
            "atrasos": total_de_atrasos,
            "taxa_de_atraso": total_de_atrasos / total_de_entregues,
        },
        "grupos_com_atraso": len(com_atraso),
        "lista_cortada": len(com_atraso) > LIMITE,
        "grupos": [
            {
                "grupo": grupo,
                "entregues": entregues[grupo],
                "atrasos": atrasos[grupo],
                "taxa_de_atraso": atrasos[grupo] / entregues[grupo],
                "participacao": atrasos[grupo] / total_de_atrasos,
            }
            for grupo in com_atraso[:LIMITE]
        ],
    }


@pytest.fixture(scope="module")
def mcp(criar_mcp):
    return criar_mcp(chaves=ChavesLocais(CHAVE))


@pytest.fixture(scope="module")
def respostas(mcp):
    token = _token_de(Perfil.VENDAS)
    return {
        (agrupamento, periodo): chamar(
            mcp, token, FERRAMENTA, {"agrupamento": agrupamento, "periodo": periodo}
        )
        for agrupamento in AGRUPAMENTOS
        for periodo in PERIODOS
    }


@pytest.mark.parametrize("periodo", PERIODOS)
@pytest.mark.parametrize("agrupamento", AGRUPAMENTOS)
def test_grupos_ordem_limite_participacao_e_totais_batem_com_os_dados_de_origem(
    respostas, conexao_dono, agrupamento, periodo
):
    resultado = respostas[agrupamento, periodo]

    assert not resultado.is_error
    assert resultado.structured_content == _esperado(conexao_dono, agrupamento, periodo)


@pytest.mark.parametrize("periodo", PERIODOS)
@pytest.mark.parametrize("agrupamento", AGRUPAMENTOS)
def test_prazo_vencido_e_em_transito_nao_entram(respostas, conexao_dono, agrupamento, periodo):
    """Taxa de atraso do glossário: só os pedidos entregues contam."""
    por_situacao = Counter(
        situacao for *_, situacao in conexao_dono.execute(_NA_ORIGEM, PERIODOS[periodo])
    )
    total = respostas[agrupamento, periodo].structured_content["total"]

    assert por_situacao["Prazo vencido"] > 0
    assert por_situacao["Em trânsito"] > 0
    assert total["atrasos"] == por_situacao["Entregue com atraso"]
    assert total["entregues"] == (
        por_situacao["Entregue no prazo"] + por_situacao["Entregue com atraso"]
    )


@pytest.mark.parametrize("periodo", PERIODOS)
def test_o_total_e_o_mesmo_nos_dois_agrupamentos_e_bate_com_os_indicadores(mcp, respostas, periodo):
    """O agrupamento reparte os mesmos pedidos; a taxa de atraso é a de `vendas_indicadores`."""
    indicadores = chamar(
        mcp, _token_de(Perfil.VENDAS), "vendas_indicadores", {"periodo": periodo}
    ).structured_content["taxa_de_atraso"]
    total = respostas["rota", periodo].structured_content["total"]

    assert total == respostas["lojista", periodo].structured_content["total"]
    assert total["atrasos"] == indicadores["atrasos"]
    assert total["taxa_de_atraso"] == indicadores["atual"]


@pytest.mark.parametrize("periodo", PERIODOS)
@pytest.mark.parametrize("agrupamento", AGRUPAMENTOS)
def test_a_lista_traz_so_os_10_primeiros_e_diz_que_foi_cortada(respostas, agrupamento, periodo):
    """Na carga padrão, todo período tem mais de 10 rotas e mais de 10 lojistas com atraso."""
    corpo = respostas[agrupamento, periodo].structured_content
    atrasos = [grupo["atrasos"] for grupo in corpo["grupos"]]

    assert len(corpo["grupos"]) == LIMITE
    assert corpo["grupos_com_atraso"] > LIMITE
    assert corpo["lista_cortada"] is True
    assert atrasos == sorted(atrasos, reverse=True)
    assert min(atrasos) >= 1
    assert sum(grupo["participacao"] for grupo in corpo["grupos"]) < 1


def test_no_empate_de_atrasos_a_ordem_e_a_do_nome_do_grupo(respostas):
    """O desempate é determinístico: a mesma chamada devolve sempre a mesma lista."""
    grupos = respostas["rota", "30d"].structured_content["grupos"]
    empatados = [
        (anterior["grupo"], seguinte["grupo"])
        for anterior, seguinte in zip(grupos, grupos[1:], strict=False)
        if anterior["atrasos"] == seguinte["atrasos"]
    ]

    assert empatados
    for anterior, seguinte in empatados:
        assert anterior < seguinte


def test_a_rota_vai_da_uf_do_lojista_a_uf_do_cliente_e_o_lojista_vem_pelo_nome(
    respostas, conexao_dono
):
    rotas = {
        f"{do_lojista} → {do_cliente}"
        for do_lojista, do_cliente in conexao_dono.execute(
            """
            select distinct l.uf, c.uf
            from dados_de_origem.pedido p
            join dados_de_origem.lojista l on l.id = p.lojista_id
            join dados_de_origem.cliente c on c.id = p.cliente_id
            """
        )
    }
    lojistas = {
        nome for (nome,) in conexao_dono.execute("select nome from dados_de_origem.lojista")
    }

    for periodo in PERIODOS:
        for grupo in respostas["rota", periodo].structured_content["grupos"]:
            assert grupo["grupo"] in rotas
        for grupo in respostas["lojista", periodo].structured_content["grupos"]:
            assert grupo["grupo"] in lojistas


@pytest.mark.parametrize("agrupamento", AGRUPAMENTOS)
def test_sem_periodo_vale_o_de_12_meses(mcp, respostas, agrupamento):
    sem_periodo = chamar(mcp, _token_de(Perfil.VENDAS), FERRAMENTA, {"agrupamento": agrupamento})

    assert not sem_periodo.is_error
    assert sem_periodo.structured_content == respostas[agrupamento, "12m"].structured_content


def test_resposta_tem_numeros_crus_e_nenhum_identificador_nem_nome_interno(respostas):
    for resultado in respostas.values():
        corpo = resultado.structured_content

        assert set(corpo) == {
            "periodo",
            "agrupamento",
            "total",
            "grupos_com_atraso",
            "lista_cortada",
            "grupos",
        }
        assert set(corpo["total"]) == {"entregues", "atrasos", "taxa_de_atraso"}
        for grupo in corpo["grupos"]:
            assert set(grupo) == {
                "grupo",
                "entregues",
                "atrasos",
                "taxa_de_atraso",
                "participacao",
            }
            assert isinstance(grupo["entregues"], int)
            assert isinstance(grupo["atrasos"], int)
            assert 0 < grupo["taxa_de_atraso"] <= 1
            assert 0 < grupo["participacao"] <= 1
        textos = [json.dumps(corpo, ensure_ascii=False), *(c.text for c in resultado.content)]
        for texto in textos:
            for proibido in ("cliente", "_id", "dados_de_origem", "vendas."):
                assert proibido not in texto


# --- O agrupamento é obrigatório e fechado: erro genérico, sem eco do valor (RS-08) ---


AGRUPAMENTOS_INVALIDOS = [
    {},
    {"periodo": "12m"},
    {"agrupamento": "categoria"},
    {"agrupamento": "Rota"},
    {"agrupamento": ""},
    {"agrupamento": "p.cliente_id"},
    {"agrupamento": "rota; drop table dados_de_origem.pedido"},
    {"agrupamento": ["rota", "lojista"]},
    {"agrupamento": None},
    {"agrupamento": 1},
    {"agrupamento": "rota", "periodo": "7d"},
    {"agrupamento": "rota", "limite": 50},
    {"agrupamento": "rota", "perfil": "vendas"},
]


@pytest.mark.parametrize("argumentos", AGRUPAMENTOS_INVALIDOS, ids=str)
def test_agrupamento_ausente_ou_invalido_recebe_erro_generico_sem_eco(mcp, argumentos):
    with TestClient(mcp) as http:
        resposta = chamar_pelo_protocolo(http, _token_de(Perfil.VENDAS), FERRAMENTA, argumentos)

    assert resposta.json()["result"] == {
        "content": [{"type": "text", "text": PARAMETRO_INVALIDO}],
        "isError": True,
    }


@pytest.mark.parametrize("perfil", OUTROS_PERFIS, ids=str)
@pytest.mark.parametrize(
    "argumentos", [{"agrupamento": "rota"}, {"agrupamento": "categoria"}, {}], ids=str
)
def test_outro_perfil_recebe_o_erro_de_ferramenta_inexistente_antes_dos_parametros(
    mcp, perfil, argumentos
):
    """Ordem token → perfil → parâmetros: o agrupamento, válido ou não, não muda o erro."""
    resultado = chamar(mcp, _token_de(perfil), FERRAMENTA, argumentos)

    assert texto_do_erro(resultado) == FERRAMENTA_DESCONHECIDA


def test_a_ferramenta_exige_o_agrupamento_e_deixa_o_periodo_opcional(mcp):
    """O esquema que o modelo lê: duas enumerações fechadas e nada além delas."""
    ferramenta = next(
        f for f in listar_ferramentas(mcp, _token_de(Perfil.VENDAS)) if f.name == FERRAMENTA
    )
    esquema = ferramenta.input_schema

    assert esquema["additionalProperties"] is False
    assert esquema["required"] == ["agrupamento"]
    assert set(esquema["properties"]) == {"periodo", "agrupamento"}
    assert esquema["properties"]["agrupamento"]["enum"] == AGRUPAMENTOS
    assert "default" not in esquema["properties"]["agrupamento"]
    assert esquema["properties"]["periodo"]["default"] == "12m"
    for explicado in ("taxa_de_atraso", "participacao", "prazo vencido", "lista_cortada"):
        assert explicado in ferramenta.description
