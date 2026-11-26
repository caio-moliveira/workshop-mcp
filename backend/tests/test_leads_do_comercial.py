"""GET /comercial/leads e `comercial_leads`: os leads mais recentes do período.

Os leads são os criados no período, do mais recente para o mais antigo, no máximo 20. Os valores
esperados vêm dos dados de origem, lidos com o papel dono. O banco é o da carga padrão (data de
referência 30/11/2026). A rota recebe só o período; a ferramenta aceita ainda os filtros opcionais
`canal` e `etapa`, de enumeração fechada com os valores do glossário (RF-23).

A API e o servidor MCP são criados pela fábrica, dentro do processo.
"""

from datetime import date

import pytest
from auditada import assert_auditada
from cliente_mcp import PARAMETRO_INVALIDO, chamar, listar_ferramentas, texto_do_erro
from recusa import RESPOSTA_DE_PARAMETRO_INVALIDO, pedir

from acesso import Perfil

ROTA = "/comercial/leads"
FERRAMENTA = "comercial_leads"
LIMITE = 20

PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}
CAMPOS_DO_LEAD = {"lead", "empresa", "canal", "etapa", "data_criacao", "data_fechamento"}


def _na_origem(
    conexao, inicio: date, fim: date, canal: str | None = None, etapa: str | None = None
) -> list[dict]:
    """Os leads criados no período, do mais recente para o mais antigo, como a origem os tem."""
    filtros = ""
    parametros: list = [inicio, fim]
    if canal is not None:
        filtros += " and canal = %s"
        parametros.append(canal)
    if etapa is not None:
        filtros += " and etapa = %s"
        parametros.append(etapa)
    linhas = conexao.execute(
        "select id, nome_empresa, canal, etapa, data_criacao, data_fechamento"
        " from dados_de_origem.lead"
        f" where data_criacao between %s and %s{filtros}"
        f" order by data_criacao desc, id desc limit {LIMITE}",
        parametros,
    ).fetchall()
    return [
        {
            "lead": lead,
            "empresa": empresa,
            "canal": canal_do_lead,
            "etapa": etapa_do_lead,
            "data_criacao": criacao.isoformat(),
            "data_fechamento": fechamento.isoformat() if fechamento else None,
        }
        for lead, empresa, canal_do_lead, etapa_do_lead, criacao, fechamento in linhas
    ]


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.COMERCIAL)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_rota_devolve_os_20_leads_mais_recentes_do_periodo(respostas, conexao_dono, periodo):
    inicio, fim = PERIODOS[periodo]
    resposta = respostas[periodo]

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["periodo"] == {"inicio": inicio.isoformat(), "fim": fim.isoformat()}
    assert corpo["leads"] == _na_origem(conexao_dono, inicio, fim)
    assert len(corpo["leads"]) == LIMITE
    criacoes = [lead["data_criacao"] for lead in corpo["leads"]]
    assert criacoes == sorted(criacoes, reverse=True)


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.COMERCIAL))

    assert resposta.json() == respostas["12m"].json()


@pytest.mark.parametrize(
    "filtros",
    [{"canal": "Indicação"}, {"etapa": "Proposta"}, {"canal": "Indicação", "etapa": "Proposta"}],
    ids=str,
)
def test_a_rota_nao_aceita_canal_nem_etapa(api, token_de, filtros):
    resposta = pedir(api, ROTA, token_de(Perfil.COMERCIAL), periodo="12m", **filtros)

    assert resposta.status_code == 400
    assert resposta.json() == RESPOSTA_DE_PARAMETRO_INVALIDO


def test_a_resposta_nao_traz_o_email_de_contato_nem_nada_do_lojista(respostas):
    corpo = respostas["24m"].json()

    assert set(corpo) == {"periodo", "leads"}
    for lead in corpo["leads"]:
        assert set(lead) == CAMPOS_DO_LEAD
        assert isinstance(lead["lead"], int)
    texto = respostas["24m"].text
    for proibido in ("email", "@", "lojista", "cnpj", "_id", "dados_de_origem", "comercial."):
        assert proibido not in texto


def test_o_lead_que_nao_fechou_vem_sem_data_de_fechamento(respostas):
    """Um lead leva de 15 a 75 dias para fechar: entre os mais recentes há os que não fecharam."""
    leads = respostas["24m"].json()["leads"]

    assert [lead for lead in leads if lead["data_fechamento"] is None]
    for lead in leads:
        assert (lead["data_fechamento"] is not None) == (lead["etapa"] == "Fechado")


# --- A ferramenta ---


@pytest.fixture(scope="module")
def mcp(criar_mcp):
    return criar_mcp()


def test_a_ferramenta_aparece_so_para_o_comercial(mcp, token_de):
    quem_ve = {
        perfil
        for perfil in Perfil
        if FERRAMENTA in {f.name for f in listar_ferramentas(mcp, token_de(perfil))}
    }

    assert quem_ve == {Perfil.COMERCIAL}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_sem_filtros_devolve_o_mesmo_que_a_rota(mcp, respostas, token_de, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    token = token_de(Perfil.COMERCIAL)

    resultado = chamar(mcp, token, FERRAMENTA, {"periodo": periodo})

    assert not resultado.is_error
    assert resultado.structured_content == respostas[periodo].json()
    assert_auditada(token, FERRAMENTA, {"periodo": periodo}, "permitida")


@pytest.mark.parametrize(
    ("periodo", "filtros"),
    [
        ("12m", {"canal": "Indicação"}),
        ("12m", {"canal": "Prospecção ativa"}),
        ("12m", {"etapa": "Proposta"}),
        ("24m", {"etapa": "Fechado"}),
        ("12m", {"canal": "Indicação", "etapa": "Qualificado"}),
        ("24m", {"canal": "Mídia paga", "etapa": "Fechado"}),
    ],
    ids=str,
)
def test_com_filtros_so_os_leads_do_recorte(mcp, token_de, conexao_dono, periodo, filtros):
    token = token_de(Perfil.COMERCIAL)
    argumentos = {"periodo": periodo, **filtros}

    resultado = chamar(mcp, token, FERRAMENTA, argumentos)

    assert not resultado.is_error
    leads = resultado.structured_content["leads"]
    assert leads == _na_origem(conexao_dono, *PERIODOS[periodo], **filtros)
    assert leads
    for filtro, valor in filtros.items():
        assert {lead[filtro] for lead in leads} == {valor}
    assert_auditada(token, FERRAMENTA, argumentos, "permitida")


def test_o_lead_fechado_vem_com_a_data_de_fechamento(mcp, token_de):
    resultado = chamar(mcp, token_de(Perfil.COMERCIAL), FERRAMENTA, {"etapa": "Fechado"})

    leads = resultado.structured_content["leads"]
    assert len(leads) == LIMITE
    for lead in leads:
        assert lead["data_fechamento"] >= lead["data_criacao"]


@pytest.mark.parametrize(
    ("periodo", "filtros"),
    [
        # Nenhum lead criado nos últimos 30 dias chegou à etapa Proposta nos dados atuais.
        ("30d", {"etapa": "Proposta"}),
        # E nenhum lead de Indicação está em Proposta, em período nenhum.
        ("24m", {"canal": "Indicação", "etapa": "Proposta"}),
    ],
    ids=str,
)
def test_recorte_sem_leads_devolve_lista_vazia(mcp, token_de, conexao_dono, periodo, filtros):
    token = token_de(Perfil.COMERCIAL)
    argumentos = {"periodo": periodo, **filtros}
    inicio, fim = PERIODOS[periodo]
    assert _na_origem(conexao_dono, inicio, fim, **filtros) == []

    resultado = chamar(mcp, token, FERRAMENTA, argumentos)

    assert not resultado.is_error
    assert resultado.structured_content == {
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "leads": [],
    }
    assert_auditada(token, FERRAMENTA, argumentos, "permitida")


@pytest.mark.parametrize(
    "argumentos",
    [
        {"canal": "Parcerias"},
        {"canal": "Indicacao"},
        {"canal": "Midia paga"},
        {"canal": "indicação"},
        {"canal": "Indicação "},
        {"canal": ""},
        {"canal": None},
        {"canal": ["Indicação"]},
        {"canal": "Proposta"},
        {"etapa": "Negociação"},
        {"etapa": "proposta"},
        {"etapa": "Indicação"},
        {"etapa": 4},
        {"etapa": None},
        {"canal": "Indicação", "etapa": "Em proposta"},
        {"canal": "Indicação", "etapa": "Proposta", "email": "a@b.com"},
        {"etapa": "Fechado", "lojista": 1},
        {"periodo": "7d", "canal": "Indicação"},
    ],
    ids=str,
)
def test_valor_fora_da_enumeracao_e_campo_extra_sao_parametro_invalido(mcp, token_de, argumentos):
    token = token_de(Perfil.COMERCIAL)

    resultado = chamar(mcp, token, FERRAMENTA, argumentos)

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO
    assert_auditada(token, FERRAMENTA, argumentos, "parametro_invalido")


def test_a_descricao_nao_marca_a_empresa_como_conteudo_nao_confiavel(mcp, token_de):
    """A empresa é texto gerado, não escrito por clientes: o ADR 0010 não se aplica."""
    token = token_de(Perfil.COMERCIAL)
    [ferramenta] = [f for f in listar_ferramentas(mcp, token) if f.name == FERRAMENTA]

    resultado = chamar(mcp, token, FERRAMENTA, {})

    assert "aviso" not in resultado.structured_content
    assert "instruções" not in ferramenta.description
