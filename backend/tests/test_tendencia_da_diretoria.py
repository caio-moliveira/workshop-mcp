"""GET /diretoria/tendencia e `diretoria_tendencia`: os quatro indicadores de cada ponto do período.

Os valores esperados vêm dos dados de origem, lidos com o papel dono, e são agrupados aqui em
Python, independentemente do SQL da view: o dia de cada pedido no horário de Brasília, a semana
começando na segunda e o mês no dia 1, como na evolução de Vendas. A taxa de recompra do ponto é
calculada dentro do ponto, e a de atraso segue a regra de Vendas (glossário). O banco é o da carga
padrão (data de referência 30/11/2026).
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import pytest
from auditada import assert_auditada
from cliente_mcp import PARAMETRO_INVALIDO, chamar, listar_ferramentas, texto_do_erro
from recusa import pedir

from acesso import Perfil
from consultas import diretoria

ROTA = "/diretoria/tendencia"
FERRAMENTA = "diretoria_tendencia"

# O período efetivo, contado à mão, e o agrupamento de cada um, como em Vendas.
PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30), "dia"),
    "90d": (date(2026, 9, 2), date(2026, 11, 30), "semana"),
    "12m": (date(2025, 12, 1), date(2026, 11, 30), "mes"),
    "24m": (date(2024, 12, 1), date(2026, 11, 30), "mes"),
}
# Quantos pontos cada período tem: 90 dias começam numa quarta, e a primeira semana é a da
# segunda 31/08.
PONTOS_CONHECIDOS = {"30d": 30, "90d": 14, "12m": 12, "24m": 24}

CAMPOS_DO_PONTO = {
    "inicio",
    "receita",
    "taxa_de_recompra",
    "clientes",
    "clientes_com_recompra",
    "satisfacao",
    "avaliacoes",
    "taxa_de_atraso",
    "entregues",
    "atrasos",
}

# Os pedidos aprovados, cada um no dia da compra em Brasília, numerado na ordem das compras do
# cliente (o primeiro não é recompra), com a situação da entrega.
_PEDIDOS_NA_ORIGEM = """
with aprovados as (
    select p.cliente_id, (p.momento_compra at time zone 'America/Sao_Paulo')::date as dia,
           g.valor, e.situacao,
           row_number() over (partition by p.cliente_id order by p.momento_compra, p.id) as ordem
    from dados_de_origem.pedido p
    join dados_de_origem.pagamento g on g.pedido_id = p.id
    left join dados_de_origem.entrega e on e.pedido_id = p.id
    where g.situacao = 'Aprovado'
)
select cliente_id, dia, valor, situacao, ordem from aprovados where dia between %s and %s
"""
_AVALIACOES_NA_ORIGEM = """
select data_avaliacao, nota from dados_de_origem.avaliacao
where data_avaliacao between %s and %s
"""


def _inicio_do_ponto(dia: date, agrupamento: str) -> date:
    if agrupamento == "dia":
        return dia
    if agrupamento == "semana":
        return dia - timedelta(days=dia.weekday())
    return dia.replace(day=1)


def _na_origem(conexao, periodo: str) -> list[dict]:
    """Os pontos do período, em ordem, calculados à mão dos dados de origem."""
    inicio, fim, agrupamento = PERIODOS[periodo]
    clientes = defaultdict(set)
    com_recompra = defaultdict(set)
    receita = defaultdict(float)
    entregues = defaultdict(int)
    atrasos = defaultdict(int)
    notas = defaultdict(list)
    for cliente, dia, valor, situacao, ordem in conexao.execute(_PEDIDOS_NA_ORIGEM, (inicio, fim)):
        ponto = _inicio_do_ponto(dia, agrupamento)
        clientes[ponto].add(cliente)
        if ordem > 1:
            com_recompra[ponto].add(cliente)
        receita[ponto] += float(valor)
        if situacao in ("Entregue no prazo", "Entregue com atraso"):
            entregues[ponto] += 1
            atrasos[ponto] += situacao == "Entregue com atraso"
    for dia, nota in conexao.execute(_AVALIACOES_NA_ORIGEM, (inicio, fim)):
        notas[_inicio_do_ponto(dia, agrupamento)].append(nota)

    inicios = sorted(
        {
            _inicio_do_ponto(inicio + timedelta(d), agrupamento)
            for d in range((fim - inicio).days + 1)
        }
    )
    return [
        {
            "inicio": ponto.isoformat(),
            "receita": receita[ponto],
            "clientes": len(clientes[ponto]),
            "clientes_com_recompra": len(com_recompra[ponto]),
            "avaliacoes": len(notas[ponto]),
            "satisfacao": sum(notas[ponto]) / len(notas[ponto]) if notas[ponto] else None,
            "entregues": entregues[ponto],
            "atrasos": atrasos[ponto],
        }
        for ponto in inicios
    ]


@pytest.fixture(scope="module")
def mcp(criar_mcp):
    return criar_mcp()


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.DIRETORIA)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_pontos_na_granularidade_de_vendas_e_em_ordem(respostas, periodo):
    inicio, fim, agrupamento = PERIODOS[periodo]
    resposta = respostas[periodo]

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["periodo"] == {"inicio": inicio.isoformat(), "fim": fim.isoformat()}
    assert corpo["agrupamento"] == agrupamento
    inicios = [ponto["inicio"] for ponto in corpo["pontos"]]
    assert len(inicios) == PONTOS_CONHECIDOS[periodo]
    assert inicios == sorted(inicios)
    assert inicios[0] == _inicio_do_ponto(inicio, agrupamento).isoformat()


@pytest.mark.parametrize("periodo", PERIODOS)
def test_cada_ponto_bate_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    esperados = _na_origem(conexao_dono, periodo)
    pontos = respostas[periodo].json()["pontos"]

    assert [p["inicio"] for p in pontos] == [e["inicio"] for e in esperados]
    for ponto, esperado in zip(pontos, esperados, strict=True):
        assert set(ponto) == CAMPOS_DO_PONTO
        assert ponto["receita"] == pytest.approx(esperado["receita"]), ponto["inicio"]
        for contagem in ("clientes", "clientes_com_recompra", "avaliacoes", "entregues", "atrasos"):
            assert ponto[contagem] == esperado[contagem], (ponto["inicio"], contagem)
        assert ponto["taxa_de_recompra"] == pytest.approx(
            esperado["clientes_com_recompra"] / esperado["clientes"]
        )
        assert ponto["satisfacao"] == pytest.approx(esperado["satisfacao"])
        if esperado["entregues"]:
            assert ponto["taxa_de_atraso"] == pytest.approx(
                esperado["atrasos"] / esperado["entregues"]
            )


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_receita_dos_pontos_soma_a_do_cartao(respostas, criar_api, token_de, periodo):
    cartao = pedir(
        criar_api(), "/diretoria/indicadores", token_de(Perfil.DIRETORIA), periodo=periodo
    ).json()

    soma = sum(ponto["receita"] for ponto in respostas[periodo].json()["pontos"])

    assert soma == pytest.approx(cartao["receita"]["atual"])


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_receita_de_cada_ponto_e_a_da_evolucao_de_vendas(respostas, api, token_de, periodo):
    """O mesmo número em dois perfis: a Diretoria não tem outra regra de data."""
    de_vendas = pedir(api, "/vendas/evolucao", token_de(Perfil.VENDAS), periodo=periodo).json()

    assert [(p["inicio"], p["receita"]) for p in respostas[periodo].json()["pontos"]] == [
        (p["inicio"], pytest.approx(p["receita"])) for p in de_vendas["pontos"]
    ]


def test_ponto_sem_entrega_vem_com_a_taxa_de_atraso_vazia_sem_quebrar_a_serie(respostas):
    """Os pedidos dos últimos dias ainda estão em trânsito: nenhum entregue."""
    pontos = respostas["30d"].json()["pontos"]
    sem_entrega = [ponto for ponto in pontos if ponto["entregues"] == 0]

    assert sem_entrega
    assert len(pontos) == PONTOS_CONHECIDOS["30d"]
    for ponto in sem_entrega:
        assert ponto["taxa_de_atraso"] is None
        assert ponto["atrasos"] == 0
        assert ponto["receita"] > 0
        assert ponto["satisfacao"] is not None


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.DIRETORIA))

    assert resposta.json() == respostas["12m"].json()


@pytest.mark.parametrize("periodo", ["7d", "", "12M", "todos"])
def test_periodo_fora_da_enumeracao_e_parametro_invalido(api, token_de, periodo):
    resposta = pedir(api, ROTA, token_de(Perfil.DIRETORIA), periodo=periodo)

    assert resposta.status_code == 400


def test_resposta_tem_numeros_crus_e_nenhum_nome_interno(respostas):
    texto = respostas["30d"].text

    for proibido in ("_id", 'cliente"', "contagem", "dados_de_origem", "base_da_diretoria"):
        assert proibido not in texto


def test_a_ferramenta_aparece_so_para_a_diretoria(mcp, token_de):
    quem_ve = {
        perfil
        for perfil in Perfil
        if FERRAMENTA in {f.name for f in listar_ferramentas(mcp, token_de(perfil))}
    }

    assert quem_ve == {Perfil.DIRETORIA}


def test_a_descricao_diz_como_cada_indicador_do_ponto_e_calculado(mcp, token_de):
    [publicada] = [
        f for f in listar_ferramentas(mcp, token_de(Perfil.DIRETORIA)) if f.name == FERRAMENTA
    ]
    descricao = publicada.description

    for trecho in (
        "'receita'",
        "'taxa_de_recompra'",
        "dentro do ponto",
        "'satisfacao'",
        "'taxa_de_atraso'",
        "prazo vencido",
        "dia em 30 dias",
        "retenção não entra",
    ):
        assert trecho in descricao, trecho


@pytest.mark.parametrize(
    "argumentos",
    [
        {"periodo": "7d"},
        {"periodo": ""},
        {"periodo": None},
        {"periodo": 30},
        {"periodo": "30d", "agrupamento": "dia"},
        {"periodo": "30d", "canal": "Mídia paga"},
        {"inicio": "2026-11-01"},
    ],
    ids=str,
)
def test_periodo_fora_da_enumeracao_e_campo_extra_sao_parametro_invalido(mcp, token_de, argumentos):
    token = token_de(Perfil.DIRETORIA)

    resultado = chamar(mcp, token, FERRAMENTA, argumentos)

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO
    assert_auditada(token, FERRAMENTA, argumentos, "parametro_invalido")


def test_sem_periodo_a_ferramenta_devolve_os_12_meses(mcp, token_de):
    token = token_de(Perfil.DIRETORIA)

    sem_periodo = chamar(mcp, token, FERRAMENTA, {})
    com_12_meses = chamar(mcp, token, FERRAMENTA, {"periodo": "12m"})

    assert not sem_periodo.is_error
    assert sem_periodo.structured_content == com_12_meses.structured_content


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_conteudo_da_rota_e_fica_na_auditoria(
    mcp, token_de, respostas, periodo
):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    token = token_de(Perfil.DIRETORIA)

    resultado = chamar(mcp, token, FERRAMENTA, {"periodo": periodo})

    assert not resultado.is_error
    assert resultado.structured_content == respostas[periodo].json()
    assert_auditada(token, FERRAMENTA, {"periodo": periodo}, "permitida")


def test_ponto_sem_avaliacao_nem_cliente_vem_com_os_indicadores_vazios():
    """Nos dados da carga todo ponto tem avaliação e cliente; a regra vale mesmo assim."""
    ponto = diretoria.ponto_da_tendencia(
        date(2026, 11, 30),
        clientes=0,
        clientes_com_recompra=0,
        receita=Decimal("0"),
        avaliacoes=0,
        satisfacao=None,
        entregues=0,
        atrasos=0,
    )

    assert ponto == {
        "inicio": "2026-11-30",
        "receita": 0.0,
        "taxa_de_recompra": None,
        "clientes": 0,
        "clientes_com_recompra": 0,
        "satisfacao": None,
        "avaliacoes": 0,
        "taxa_de_atraso": None,
        "entregues": 0,
        "atrasos": 0,
    }
