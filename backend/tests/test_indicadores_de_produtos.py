"""GET /produtos/indicadores: o catálogo e os indicadores das avaliações do período e do anterior.

Os valores esperados vêm de consultas independentes, feitas com o papel dono nos dados de origem:
o período filtra pela data da avaliação, e o catálogo não depende dele (glossário). O banco é o da
carga padrão (data de referência 30/11/2026). A ferramenta `produtos_indicadores` devolve o mesmo
conteúdo, e a chamada fica na auditoria com o usuário e o perfil de Produtos.
"""

import os
from datetime import date

import httpx
import pytest
from apoio import ultima_chamada_de
from cliente_mcp import MCP_DO_AMBIENTE, chamar
from provedor import conteudo
from recusa import pedir

from acesso import Perfil

ROTA = "/produtos/indicadores"
FERRAMENTA = "produtos_indicadores"
API_DO_AMBIENTE = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"

# Os períodos que terminam em 30/11/2026 e os anteriores de mesmo tamanho, como em Vendas. Nos 24
# meses o anterior começaria antes do início dos dados, e não há com o que comparar.
PERIODOS = {
    "30d": ((date(2026, 11, 1), date(2026, 11, 30)), (date(2026, 10, 2), date(2026, 10, 31))),
    "90d": ((date(2026, 9, 2), date(2026, 11, 30)), (date(2026, 6, 4), date(2026, 9, 1))),
    "12m": ((date(2025, 12, 1), date(2026, 11, 30)), (date(2024, 12, 1), date(2025, 11, 30))),
    "24m": ((date(2024, 12, 1), date(2026, 11, 30)), None),
}
# Produtos mal avaliados com os dados atuais (spec #77), contados à parte nos dados de origem.
MAL_AVALIADOS_CONHECIDOS = {"30d": 4, "90d": 26, "12m": 20, "24m": 7}

INDICADORES_DO_PERIODO = (
    "produtos_avaliados",
    "nota_media",
    "avaliacoes",
    "reclamacoes",
    "produtos_mal_avaliados",
)

_NA_ORIGEM = """
with do_periodo as (
    select produto_id, nota from dados_de_origem.avaliacao where data_avaliacao between %s and %s
),
por_produto as (
    select produto_id, avg(nota) as media, count(*) as quantas from do_periodo group by produto_id
)
select
    (select count(distinct produto_id) from do_periodo),
    (select avg(nota) from do_periodo),
    (select count(*) from do_periodo),
    (select count(*) from do_periodo where nota in (1, 2)),
    (select count(*) from por_produto where media < 3 and quantas >= 3)
"""


def _na_origem(conexao, datas) -> dict:
    linha = conexao.execute(_NA_ORIGEM, datas).fetchone()
    esperado = dict(zip(INDICADORES_DO_PERIODO, linha, strict=True))
    esperado["nota_media"] = float(esperado["nota_media"])
    return esperado


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.PRODUTOS)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    (inicio, fim), _ = PERIODOS[periodo]
    resposta = respostas[periodo]

    assert resposta.status_code == 200
    assert resposta.json()["periodo"] == {"inicio": inicio.isoformat(), "fim": fim.isoformat()}


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.PRODUTOS))

    assert resposta.json() == respostas["12m"].json()


@pytest.mark.parametrize("periodo", PERIODOS)
def test_o_catalogo_tem_os_2000_produtos_em_qualquer_periodo(respostas, periodo):
    assert respostas[periodo].json()["catalogo"] == 2000


@pytest.mark.parametrize("periodo", PERIODOS)
def test_indicadores_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    atual, anterior = PERIODOS[periodo]
    corpo = respostas[periodo].json()
    esperado = _na_origem(conexao_dono, atual)
    esperado_antes = _na_origem(conexao_dono, anterior) if anterior else None

    for indicador in INDICADORES_DO_PERIODO:
        assert corpo[indicador]["atual"] == pytest.approx(esperado[indicador]), indicador
        if esperado_antes is None:
            assert corpo[indicador]["anterior"] is None, indicador
        else:
            assert corpo[indicador]["anterior"] == pytest.approx(esperado_antes[indicador]), (
                indicador
            )


@pytest.mark.parametrize("periodo", PERIODOS)
def test_mal_avaliado_exige_media_abaixo_de_3_com_pelo_menos_3_avaliacoes(respostas, periodo):
    corpo = respostas[periodo].json()

    assert corpo["produtos_mal_avaliados"]["atual"] == MAL_AVALIADOS_CONHECIDOS[periodo]


def test_o_minimo_de_3_avaliacoes_deixa_de_fora_produtos_com_media_baixa(respostas, conexao_dono):
    """Sem o mínimo, os produtos com uma ou duas notas baixas no período também contariam."""
    (inicio, fim), _ = PERIODOS["30d"]
    so_pela_media = conexao_dono.execute(
        """
        select count(*) from (
            select produto_id from dados_de_origem.avaliacao
            where data_avaliacao between %s and %s
            group by produto_id having avg(nota) < 3
        ) t
        """,
        (inicio, fim),
    ).fetchone()[0]

    assert so_pela_media > respostas["30d"].json()["produtos_mal_avaliados"]["atual"]


def test_resposta_tem_numeros_crus_e_nenhum_nome_interno(respostas):
    corpo = respostas["12m"].json()

    assert set(corpo) == {"periodo", "catalogo", *INDICADORES_DO_PERIODO}
    assert isinstance(corpo["catalogo"], int)
    for contagem in ("produtos_avaliados", "avaliacoes", "reclamacoes", "produtos_mal_avaliados"):
        assert isinstance(corpo[contagem]["atual"], int), contagem
    assert 1 <= corpo["nota_media"]["atual"] <= 5
    texto = respostas["12m"].text
    for proibido in ("cliente", "pedido", "lojista", "_id", "dados_de_origem", "produtos."):
        assert proibido not in texto


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_conteudo_da_rota_e_fica_na_auditoria(token_de, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    token = token_de(Perfil.PRODUTOS)
    with httpx.Client(base_url=API_DO_AMBIENTE, timeout=10) as api:
        da_api = pedir(api, ROTA, token, periodo=periodo)

    resultado = chamar(MCP_DO_AMBIENTE, token, FERRAMENTA, {"periodo": periodo})

    assert da_api.status_code == 200
    assert not resultado.is_error
    assert resultado.structured_content == da_api.json()
    do_token = conteudo(token)
    linha = ultima_chamada_de(do_token["sub"])
    assert linha is not None
    assert linha["nome_do_usuario"] == do_token["name"]
    assert linha["perfil"] == "produtos"
    assert linha["ferramenta"] == FERRAMENTA
    assert linha["parametros"] == {"periodo": periodo}
    assert linha["resultado"] == "permitida"
