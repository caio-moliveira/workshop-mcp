"""GET /diretoria/indicadores: a receita, a taxa de recompra, a satisfação e a retenção.

Os valores esperados vêm de consultas independentes, feitas com o papel dono nos dados de origem,
com as regras de data dos outros perfis: o pedido entra no período pelo dia da compra no horário
de Brasília, como em Vendas, e a avaliação pela data dela, como em Produtos (glossário). O banco é
o da carga padrão (data de referência 30/11/2026). A ferramenta `diretoria_indicadores` devolve o
mesmo conteúdo, e a chamada fica na auditoria com o usuário e o perfil da Diretoria.
"""

import os
from datetime import date

import httpx
import pytest
from auditada import assert_auditada
from cliente_mcp import (
    MCP_DO_AMBIENTE,
    PARAMETRO_INVALIDO,
    chamar,
    listar_ferramentas,
    texto_do_erro,
)
from recusa import pedir

from acesso import Perfil

ROTA = "/diretoria/indicadores"
FERRAMENTA = "diretoria_indicadores"
API_DO_AMBIENTE = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"

# Os períodos que terminam em 30/11/2026, o anterior de mesmo tamanho e o anterior a esse, como
# em Vendas: um período que começaria antes do início dos dados (01/12/2024) não existe.
PERIODOS = {
    "30d": (
        (date(2026, 11, 1), date(2026, 11, 30)),
        (date(2026, 10, 2), date(2026, 10, 31)),
        (date(2026, 9, 2), date(2026, 10, 1)),
    ),
    "90d": (
        (date(2026, 9, 2), date(2026, 11, 30)),
        (date(2026, 6, 4), date(2026, 9, 1)),
        (date(2026, 3, 6), date(2026, 6, 3)),
    ),
    "12m": ((date(2025, 12, 1), date(2026, 11, 30)), (date(2024, 12, 1), date(2025, 11, 30)), None),
    "24m": ((date(2024, 12, 1), date(2026, 11, 30)), None, None),
}

# Os valores dos dados atuais (spec #96), medidos à parte nos dados de origem com a regra de data
# de Brasília: os clientes com pedido aprovado, os que fizeram recompra no período e, na
# retenção, os do período anterior que compraram de novo, dos que havia no anterior.
CLIENTES_CONHECIDOS = {"30d": 2173, "90d": 4726, "12m": 15379, "24m": 27301}
COM_RECOMPRA_CONHECIDOS = {"30d": 308, "90d": 593, "12m": 1204, "24m": 1365}
RETENCAO_CONHECIDA = {"30d": (11, 1296), "90d": (191, 3545), "12m": (573, 12495)}

CAMPOS = {"periodo", "receita", "taxa_de_recompra", "satisfacao", "retencao"}

# Os pedidos aprovados, cada um no dia da compra em Brasília e numerado na ordem das compras do
# cliente: o primeiro não é recompra.
_APROVADOS = """
    aprovados as (
        select p.cliente_id, (p.momento_compra at time zone 'America/Sao_Paulo')::date as dia,
               g.valor,
               row_number() over (partition by p.cliente_id order by p.momento_compra, p.id)
                   as ordem
        from dados_de_origem.pedido p
        join dados_de_origem.pagamento g on g.pedido_id = p.id
        where g.situacao = 'Aprovado'
    )
"""


def _clientes_na_origem(conexao, datas) -> tuple[int, int]:
    """Os clientes com pedido aprovado no período e os que fizeram recompra nele."""
    return conexao.execute(
        f"""
        with {_APROVADOS}
        select count(distinct cliente_id), count(distinct cliente_id) filter (where ordem > 1)
        from aprovados where dia between %s and %s
        """,
        datas,
    ).fetchone()


def _receita_na_origem(conexao, datas) -> float:
    return float(
        conexao.execute(
            f"with {_APROVADOS} select sum(valor) from aprovados where dia between %s and %s",
            datas,
        ).fetchone()[0]
    )


def _satisfacao_na_origem(conexao, datas) -> tuple[float, int]:
    media, avaliacoes = conexao.execute(
        "select avg(nota), count(*) from dados_de_origem.avaliacao"
        " where data_avaliacao between %s and %s",
        datas,
    ).fetchone()
    return float(media), avaliacoes


def _retencao_na_origem(conexao, datas, anteriores) -> tuple[int, int]:
    """Dos clientes com pedido aprovado no anterior, os que tiveram outro no período, e quantos
    eram no anterior."""
    return conexao.execute(
        f"""
        with {_APROVADOS},
        antes as (select distinct cliente_id from aprovados where dia between %s and %s),
        agora as (select distinct cliente_id from aprovados where dia between %s and %s)
        select (select count(*) from antes join agora using (cliente_id)),
               (select count(*) from antes)
        """,
        (*anteriores, *datas),
    ).fetchone()


@pytest.fixture(scope="module")
def mcp(criar_mcp):
    return criar_mcp()


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.DIRETORIA)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    inicio, fim = PERIODOS[periodo][0]
    resposta = respostas[periodo]

    assert resposta.status_code == 200
    assert resposta.json()["periodo"] == {"inicio": inicio.isoformat(), "fim": fim.isoformat()}


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.DIRETORIA))

    assert resposta.json() == respostas["12m"].json()


@pytest.mark.parametrize("periodo", ["7d", "", "12M", "todos"])
def test_periodo_fora_da_enumeracao_e_parametro_invalido(api, token_de, periodo):
    resposta = pedir(api, ROTA, token_de(Perfil.DIRETORIA), periodo=periodo)

    assert resposta.status_code == 400


@pytest.mark.parametrize("periodo", PERIODOS)
def test_clientes_e_recompra_sao_os_conhecidos_dos_dados_atuais(respostas, periodo):
    recompra = respostas[periodo].json()["taxa_de_recompra"]

    assert recompra["clientes"] == CLIENTES_CONHECIDOS[periodo]
    assert recompra["clientes_com_recompra"] == COM_RECOMPRA_CONHECIDOS[periodo]
    assert recompra["atual"] == pytest.approx(
        COM_RECOMPRA_CONHECIDOS[periodo] / CLIENTES_CONHECIDOS[periodo]
    )


@pytest.mark.parametrize("periodo", RETENCAO_CONHECIDA)
def test_retencao_e_a_conhecida_dos_dados_atuais(respostas, periodo):
    retidos, do_anterior = RETENCAO_CONHECIDA[periodo]
    retencao = respostas[periodo].json()["retencao"]

    assert retencao["retidos"] == retidos
    assert retencao["clientes_do_periodo_anterior"] == do_anterior
    assert retencao["atual"] == pytest.approx(retidos / do_anterior)


@pytest.mark.parametrize("periodo", PERIODOS)
def test_recompra_e_receita_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    atual, anterior, _ = PERIODOS[periodo]
    corpo = respostas[periodo].json()
    clientes, com_recompra = _clientes_na_origem(conexao_dono, atual)

    assert corpo["taxa_de_recompra"]["clientes"] == clientes
    assert corpo["taxa_de_recompra"]["clientes_com_recompra"] == com_recompra
    assert corpo["receita"]["atual"] == pytest.approx(_receita_na_origem(conexao_dono, atual))
    if anterior is None:
        assert corpo["receita"]["anterior"] is None
        assert corpo["taxa_de_recompra"]["anterior"] is None
    else:
        clientes_antes, com_recompra_antes = _clientes_na_origem(conexao_dono, anterior)
        assert corpo["receita"]["anterior"] == pytest.approx(
            _receita_na_origem(conexao_dono, anterior)
        )
        assert corpo["taxa_de_recompra"]["anterior"] == pytest.approx(
            com_recompra_antes / clientes_antes
        )


@pytest.mark.parametrize("periodo", PERIODOS)
def test_satisfacao_bate_com_as_avaliacoes_dos_dados_de_origem(respostas, conexao_dono, periodo):
    atual, anterior, _ = PERIODOS[periodo]
    satisfacao = respostas[periodo].json()["satisfacao"]
    media, avaliacoes = _satisfacao_na_origem(conexao_dono, atual)

    assert satisfacao["atual"] == pytest.approx(media)
    assert satisfacao["avaliacoes"] == avaliacoes
    if anterior is None:
        assert satisfacao["anterior"] is None
    else:
        assert satisfacao["anterior"] == pytest.approx(
            _satisfacao_na_origem(conexao_dono, anterior)[0]
        )


@pytest.mark.parametrize("periodo", PERIODOS)
def test_retencao_bate_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    atual, anterior, de_dois_antes = PERIODOS[periodo]
    retencao = respostas[periodo].json()["retencao"]

    if anterior is None:
        assert retencao == {
            "atual": None,
            "anterior": None,
            "retidos": None,
            "clientes_do_periodo_anterior": None,
        }
        return
    retidos, do_anterior = _retencao_na_origem(conexao_dono, atual, anterior)
    assert (retencao["retidos"], retencao["clientes_do_periodo_anterior"]) == (
        retidos,
        do_anterior,
    )
    assert retencao["atual"] == pytest.approx(retidos / do_anterior)
    if de_dois_antes is None:
        assert retencao["anterior"] is None
    else:
        retidos_antes, de_dois = _retencao_na_origem(conexao_dono, anterior, de_dois_antes)
        assert retencao["anterior"] == pytest.approx(retidos_antes / de_dois)


def test_em_24_meses_nenhum_indicador_tem_anterior_e_a_retencao_vem_vazia(respostas):
    corpo = respostas["24m"].json()

    for indicador in CAMPOS - {"periodo"}:
        assert corpo[indicador]["anterior"] is None, indicador
    assert corpo["retencao"]["atual"] is None


def test_em_12_meses_a_retencao_tem_valor_e_nao_tem_anterior(respostas):
    """A variação da retenção precisa de dois períodos para trás, e o de 12 meses só tem um."""
    corpo = respostas["12m"].json()

    assert corpo["retencao"]["atual"] is not None
    assert corpo["retencao"]["anterior"] is None
    for indicador in ("receita", "taxa_de_recompra", "satisfacao"):
        assert corpo[indicador]["anterior"] is not None, indicador


@pytest.mark.parametrize("periodo", ["30d", "90d"])
def test_nos_periodos_curtos_todos_os_indicadores_tem_anterior(respostas, periodo):
    corpo = respostas[periodo].json()

    for indicador in CAMPOS - {"periodo"}:
        assert corpo[indicador]["anterior"] is not None, indicador


@pytest.mark.parametrize("periodo", PERIODOS)
def test_receita_igual_a_de_vendas_e_satisfacao_igual_a_nota_media_de_produtos(
    api, token_de, respostas, periodo
):
    """O mesmo número em dois perfis, pela API: a Diretoria não tem outra regra de data."""
    corpo = respostas[periodo].json()
    de_vendas = pedir(api, "/vendas/indicadores", token_de(Perfil.VENDAS), periodo=periodo).json()
    de_produtos = pedir(
        api, "/produtos/indicadores", token_de(Perfil.PRODUTOS), periodo=periodo
    ).json()

    assert corpo["receita"] == de_vendas["receita"]
    assert {k: corpo["satisfacao"][k] for k in ("atual", "anterior")} == de_produtos["nota_media"]
    assert corpo["satisfacao"]["avaliacoes"] == de_produtos["avaliacoes"]["atual"]


def test_resposta_tem_numeros_crus_e_nenhum_nome_interno(respostas):
    corpo = respostas["30d"].json()

    assert set(corpo) == CAMPOS
    assert isinstance(corpo["taxa_de_recompra"]["clientes"], int)
    assert isinstance(corpo["retencao"]["retidos"], int)
    for taxa in ("taxa_de_recompra", "retencao"):
        assert 0 < corpo[taxa]["atual"] < 1, taxa
    assert 1 <= corpo["satisfacao"]["atual"] <= 5
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


def test_a_descricao_diz_que_a_taxa_de_recompra_e_maior_em_periodos_curtos(mcp, token_de):
    [publicada] = [
        f for f in listar_ferramentas(mcp, token_de(Perfil.DIRETORIA)) if f.name == FERRAMENTA
    ]

    assert "é maior em períodos curtos" in publicada.description
    assert "não é melhora" in publicada.description


@pytest.mark.parametrize(
    "argumentos",
    [
        {"periodo": "7d"},
        {"periodo": ""},
        {"periodo": None},
        {"periodo": 30},
        {"periodo": ["30d"]},
        {"periodo": "30d", "canal": "Mídia paga"},
        {"periodo": "30d", "cliente": 1},
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
    """O período é opcional, com o padrão de 12 meses, como em toda ferramenta."""
    token = token_de(Perfil.DIRETORIA)

    sem_periodo = chamar(mcp, token, FERRAMENTA, {})
    com_12_meses = chamar(mcp, token, FERRAMENTA, {"periodo": "12m"})

    assert not sem_periodo.is_error
    assert sem_periodo.structured_content == com_12_meses.structured_content


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_conteudo_da_rota_e_fica_na_auditoria(token_de, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    token = token_de(Perfil.DIRETORIA)
    with httpx.Client(base_url=API_DO_AMBIENTE, timeout=10) as api:
        da_api = pedir(api, ROTA, token, periodo=periodo)

    resultado = chamar(MCP_DO_AMBIENTE, token, FERRAMENTA, {"periodo": periodo})

    assert da_api.status_code == 200
    assert not resultado.is_error
    assert resultado.structured_content == da_api.json()
    assert_auditada(token, FERRAMENTA, {"periodo": periodo}, "permitida")
