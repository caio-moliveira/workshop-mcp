"""GET /comercial/indicadores: os leads, os novos lojistas, a conversão e o principal canal.

Os valores esperados vêm de consultas independentes, feitas com o papel dono nos dados de origem:
leads, leads em negociação e principal canal pela data de criação; novos lojistas e dias até
fechar pela data de fechamento (glossário). O banco é o da carga padrão (data de referência
30/11/2026). A ferramenta `comercial_indicadores` devolve o mesmo conteúdo, e a chamada fica na
auditoria com o usuário e o perfil do Comercial.
"""

import os
from datetime import date

import httpx
import pytest
from auditada import assert_auditada
from cliente_mcp import MCP_DO_AMBIENTE, chamar, listar_ferramentas
from recusa import pedir

from acesso import Perfil
from consultas import comercial as consultas_do_comercial
from consultas.periodo import Periodo

ROTA = "/comercial/indicadores"
FERRAMENTA = "comercial_indicadores"
API_DO_AMBIENTE = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"

# Os períodos que terminam em 30/11/2026 e os anteriores de mesmo tamanho, como em Vendas. Nos 24
# meses o anterior começaria antes do início dos dados, e não há com o que comparar.
PERIODOS = {
    "30d": ((date(2026, 11, 1), date(2026, 11, 30)), (date(2026, 10, 2), date(2026, 10, 31))),
    "90d": ((date(2026, 9, 2), date(2026, 11, 30)), (date(2026, 6, 4), date(2026, 9, 1))),
    "12m": ((date(2025, 12, 1), date(2026, 11, 30)), (date(2024, 12, 1), date(2025, 11, 30))),
    "24m": ((date(2024, 12, 1), date(2026, 11, 30)), None),
}
# Os valores dos dados atuais (spec #87), contados à parte nos dados de origem.
LEADS_CONHECIDOS = {"30d": 67, "90d": 197, "12m": 746, "24m": 1326}
NOVOS_LOJISTAS_CONHECIDOS = {"30d": 14, "90d": 36, "12m": 126, "24m": 220}
# Em 30 dias, Orgânico traz 19 dos 67 leads; em 12 meses, Mídia paga traz 222 dos 746.
PRINCIPAL_CANAL_CONHECIDO = {"30d": ("Orgânico", 19 / 67), "12m": ("Mídia paga", 222 / 746)}

COM_ANTERIOR = ("leads", "novos_lojistas", "conversao")
CAMPOS = {
    "periodo",
    *COM_ANTERIOR,
    "leads_em_negociacao",
    "dias_ate_fechar",
    "principal_canal",
    "parcela_do_principal_canal",
}

_NA_ORIGEM = """
select
    (select count(*) from dados_de_origem.lead where data_criacao between %(inicio)s and %(fim)s),
    (select count(*) from dados_de_origem.lead
      where data_criacao between %(inicio)s and %(fim)s
        and etapa not in ('Fechado', 'Perdido')),
    (select count(*) from dados_de_origem.lead
      where data_fechamento between %(inicio)s and %(fim)s),
    (select avg(data_fechamento - data_criacao) from dados_de_origem.lead
      where data_fechamento between %(inicio)s and %(fim)s)
"""


def _na_origem(conexao, datas) -> dict:
    inicio, fim = datas
    leads, em_negociacao, novos_lojistas, dias = conexao.execute(
        _NA_ORIGEM, {"inicio": inicio, "fim": fim}
    ).fetchone()
    return {
        "leads": leads,
        "leads_em_negociacao": em_negociacao,
        "novos_lojistas": novos_lojistas,
        "dias_ate_fechar": float(dias),
        "conversao": novos_lojistas / leads,
    }


def _canais_na_origem(conexao, datas) -> dict[str, int]:
    """Os leads criados no período em cada canal."""
    return dict(
        conexao.execute(
            "select canal, count(*) from dados_de_origem.lead"
            " where data_criacao between %s and %s group by canal",
            datas,
        ).fetchall()
    )


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.COMERCIAL)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    (inicio, fim), _ = PERIODOS[periodo]
    resposta = respostas[periodo]

    assert resposta.status_code == 200
    assert resposta.json()["periodo"] == {"inicio": inicio.isoformat(), "fim": fim.isoformat()}


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.COMERCIAL))

    assert resposta.json() == respostas["12m"].json()


@pytest.mark.parametrize("periodo", PERIODOS)
def test_leads_e_novos_lojistas_sao_os_conhecidos_dos_dados_atuais(respostas, periodo):
    corpo = respostas[periodo].json()

    assert corpo["leads"]["atual"] == LEADS_CONHECIDOS[periodo]
    assert corpo["novos_lojistas"]["atual"] == NOVOS_LOJISTAS_CONHECIDOS[periodo]


@pytest.mark.parametrize("periodo", PERIODOS)
def test_indicadores_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    atual, anterior = PERIODOS[periodo]
    corpo = respostas[periodo].json()
    esperado = _na_origem(conexao_dono, atual)
    esperado_antes = _na_origem(conexao_dono, anterior) if anterior else None

    assert corpo["leads_em_negociacao"] == esperado["leads_em_negociacao"]
    assert corpo["dias_ate_fechar"] == pytest.approx(esperado["dias_ate_fechar"])
    for indicador in COM_ANTERIOR:
        assert corpo[indicador]["atual"] == pytest.approx(esperado[indicador]), indicador
        if esperado_antes is None:
            assert corpo[indicador]["anterior"] is None, indicador
        else:
            assert corpo[indicador]["anterior"] == pytest.approx(esperado_antes[indicador]), (
                indicador
            )


@pytest.mark.parametrize("periodo", PERIODOS)
def test_conversao_e_novos_lojistas_por_leads_do_periodo_e_nao_uma_coorte(
    respostas, conexao_dono, periodo
):
    """Um lead criado antes do período pode fechar dentro dele: a coorte daria outro número."""
    inicio, fim = PERIODOS[periodo][0]
    corpo = respostas[periodo].json()
    da_coorte = conexao_dono.execute(
        "select count(*) from dados_de_origem.lead"
        " where data_criacao between %s and %s and etapa = 'Fechado'",
        (inicio, fim),
    ).fetchone()[0]

    assert corpo["conversao"]["atual"] == pytest.approx(
        NOVOS_LOJISTAS_CONHECIDOS[periodo] / LEADS_CONHECIDOS[periodo]
    )
    assert da_coorte != NOVOS_LOJISTAS_CONHECIDOS[periodo]


@pytest.mark.parametrize("periodo", PERIODOS)
def test_principal_canal_e_o_que_trouxe_mais_leads_com_a_parcela_dele(
    respostas, conexao_dono, periodo
):
    corpo = respostas[periodo].json()
    por_canal = _canais_na_origem(conexao_dono, PERIODOS[periodo][0])
    maior = max(por_canal.values())
    # Sem empate no primeiro lugar nos dados atuais: o desempate não entra na conta esperada.
    assert list(por_canal.values()).count(maior) == 1

    assert por_canal[corpo["principal_canal"]] == maior
    assert corpo["parcela_do_principal_canal"] == pytest.approx(maior / sum(por_canal.values()))


@pytest.mark.parametrize("periodo", PRINCIPAL_CANAL_CONHECIDO)
def test_principal_canal_conhecido_dos_dados_atuais(respostas, periodo):
    canal, parcela = PRINCIPAL_CANAL_CONHECIDO[periodo]
    corpo = respostas[periodo].json()

    assert corpo["principal_canal"] == canal
    assert corpo["parcela_do_principal_canal"] == pytest.approx(parcela)


def test_resposta_tem_numeros_crus_e_nenhum_nome_interno(respostas):
    corpo = respostas["12m"].json()

    assert set(corpo) == CAMPOS
    for contagem in ("leads", "novos_lojistas"):
        assert isinstance(corpo[contagem]["atual"], int), contagem
    assert isinstance(corpo["leads_em_negociacao"], int)
    # A conversão é uma razão entre dois movimentos do período: pode passar de 1.
    assert corpo["conversao"]["atual"] > 0
    assert 0 < corpo["parcela_do_principal_canal"] <= 1
    texto = respostas["12m"].text
    for proibido in ("email", "lojista_id", "pedido", "atras", "_id", "dados_de_origem", "origem"):
        assert proibido not in texto


def _principal_canal_com(conexao, leads_por_canal: dict[str, int], novos_lojistas: list[str]):
    """O principal canal dos últimos 30 dias, lido com o papel do Comercial, num período que só
    tem os leads criados de `leads_por_canal` e um novo lojista em cada canal de `novos_lojistas`.

    Quem chama abre a transação e a desfaz: os dados de origem ficam como estavam.
    """
    _, fim = PERIODOS["30d"][0]
    fora = date(2024, 12, 1)
    # Tira todo lead do período: nem criado nem fechado nele.
    conexao.execute(
        "update dados_de_origem.lead set data_criacao = %s,"
        " data_fechamento = case when data_fechamento is not null then %s::date end",
        (fora, fora),
    )
    abertos = [
        linha[0]
        for linha in conexao.execute(
            "select id from dados_de_origem.lead where etapa = 'Novo' order by id"
        ).fetchall()
    ]
    fechados = [
        linha[0]
        for linha in conexao.execute(
            "select id from dados_de_origem.lead where etapa = 'Fechado' order by id"
        ).fetchall()
    ]
    for canal, quantos in leads_por_canal.items():
        for _ in range(quantos):
            conexao.execute(
                "update dados_de_origem.lead set canal = %s, data_criacao = %s where id = %s",
                (canal, fim, abertos.pop()),
            )
    # O novo lojista fechou no período e foi criado antes dele: não soma aos leads do canal.
    for canal in novos_lojistas:
        conexao.execute(
            "update dados_de_origem.lead set canal = %s, data_fechamento = %s where id = %s",
            (canal, fim, fechados.pop()),
        )
    conexao.execute("set local role comercial")
    corpo = consultas_do_comercial.indicadores.ler(conexao, Periodo.TRINTA_DIAS)
    return corpo["principal_canal"], corpo["parcela_do_principal_canal"]


def test_no_empate_de_leads_o_principal_canal_e_o_de_mais_novos_lojistas_e_depois_o_alfabetico(
    conexao_dono,
):
    """Três canais com dois leads cada. O empate não existe nos dados atuais: só dentro de uma
    transação desfeita no fim, que nenhum outro processo vê."""
    empatados = {"Eventos": 2, "Mídia paga": 2, "Orgânico": 2}

    with conexao_dono.transaction(force_rollback=True):
        so_o_alfabeto = _principal_canal_com(conexao_dono, empatados, [])
    with conexao_dono.transaction(force_rollback=True):
        um_com_novo_lojista = _principal_canal_com(conexao_dono, empatados, ["Orgânico"])
    with conexao_dono.transaction(force_rollback=True):
        dois_com_novo_lojista = _principal_canal_com(
            conexao_dono, empatados, ["Orgânico", "Mídia paga"]
        )

    assert so_o_alfabeto == ("Eventos", pytest.approx(2 / 6))
    # Mais novos lojistas vence o empate, mesmo sendo o último na ordem alfabética.
    assert um_com_novo_lojista == ("Orgânico", pytest.approx(2 / 6))
    # Persistindo o empate entre os dois, a ordem alfabética; Eventos, sem novo lojista, não volta.
    assert dois_com_novo_lojista == ("Mídia paga", pytest.approx(2 / 6))


def test_a_descricao_diz_que_a_conversao_e_uma_razao_que_pode_passar_de_1(criar_mcp, token_de):
    [publicada] = [
        f
        for f in listar_ferramentas(criar_mcp(), token_de(Perfil.COMERCIAL))
        if f.name == FERRAMENTA
    ]

    assert (
        "novos lojistas do período ÷ leads criados no mesmo período, de 0 em diante"
        in publicada.description
    )
    assert "'parcela_do_principal_canal' é a parte dele nos leads do período, de 0 a 1" in (
        publicada.description
    )


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_conteudo_da_rota_e_fica_na_auditoria(token_de, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    token = token_de(Perfil.COMERCIAL)
    with httpx.Client(base_url=API_DO_AMBIENTE, timeout=10) as api:
        da_api = pedir(api, ROTA, token, periodo=periodo)

    resultado = chamar(MCP_DO_AMBIENTE, token, FERRAMENTA, {"periodo": periodo})

    assert da_api.status_code == 200
    assert not resultado.is_error
    assert resultado.structured_content == da_api.json()
    assert_auditada(token, FERRAMENTA, {"periodo": periodo}, "permitida")
