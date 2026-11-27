"""GET /comercial/canais: os cinco canais com leads, novos lojistas, conversão e dias médios até
fechar do período, da maior conversão para a menor.

Os valores esperados vêm de consultas independentes, feitas com o papel dono nos dados de origem:
os leads pela data de criação, os novos lojistas e os dias até fechar pela data de fechamento
(glossário). O banco é o da carga padrão (data de referência 30/11/2026). A ferramenta
`comercial_canais` devolve o mesmo conteúdo; ela é chamada no servidor MCP criado dentro do
processo.
"""

from datetime import date

import pytest
from cliente_mcp import CAMINHO, chamar, listar_ferramentas
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from recusa import pedir
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil
from consultas import comercial as consultas_do_comercial
from consultas.periodo import Periodo

ROTA = "/comercial/canais"
FERRAMENTA = "comercial_canais"
# A pergunta sugerida no painel do assistente do Comercial (frontend/src/perfis.ts).
PERGUNTA_SUGERIDA = "Qual canal traz os leads que mais convertem?"

# Os canais do glossário.
CANAIS = {"Indicação", "Orgânico", "Mídia paga", "Eventos", "Prospecção ativa"}
PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}
# Os valores dos dados atuais (spec #87): novos lojistas e leads do canal no período.
CONHECIDOS = {
    "12m": {"Mídia paga": (57, 222), "Indicação": (22, 100)},
    "30d": {"Indicação": (3, 10), "Mídia paga": (4, 16)},
}
CAMPOS_DO_CANAL = {"canal", "leads", "novos_lojistas", "conversao", "dias_ate_fechar"}

_NA_ORIGEM = """
select
    canal,
    count(*) filter (where data_criacao between %(inicio)s and %(fim)s),
    count(*) filter (where data_fechamento between %(inicio)s and %(fim)s),
    avg(data_fechamento - data_criacao)
        filter (where data_fechamento between %(inicio)s and %(fim)s)
from dados_de_origem.lead
group by canal
"""


def _na_origem(conexao, datas) -> dict[str, dict]:
    inicio, fim = datas
    return {
        canal: {
            "leads": leads,
            "novos_lojistas": novos_lojistas,
            "conversao": novos_lojistas / leads if leads else None,
            "dias_ate_fechar": None if dias is None else float(dias),
        }
        for canal, leads, novos_lojistas, dias in conexao.execute(
            _NA_ORIGEM, {"inicio": inicio, "fim": fim}
        ).fetchall()
    }


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.COMERCIAL)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_os_cinco_canais_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    resposta = respostas[periodo]
    na_origem = _na_origem(conexao_dono, PERIODOS[periodo])

    assert resposta.status_code == 200
    canais = resposta.json()["canais"]
    assert len(canais) == 5
    assert {item["canal"] for item in canais} == CANAIS
    for item in canais:
        nome = item["canal"]
        esperado = na_origem[nome]
        assert item["leads"] == esperado["leads"], nome
        assert item["novos_lojistas"] == esperado["novos_lojistas"], nome
        assert item["conversao"] == pytest.approx(esperado["conversao"]), nome
        assert item["dias_ate_fechar"] == pytest.approx(esperado["dias_ate_fechar"]), nome


@pytest.mark.parametrize("periodo", CONHECIDOS)
def test_os_canais_conhecidos_dos_dados_atuais(respostas, periodo):
    por_canal = {item["canal"]: item for item in respostas[periodo].json()["canais"]}

    for canal, (novos_lojistas, leads) in CONHECIDOS[periodo].items():
        assert (por_canal[canal]["novos_lojistas"], por_canal[canal]["leads"]) == (
            novos_lojistas,
            leads,
        ), canal
        assert por_canal[canal]["conversao"] == pytest.approx(novos_lojistas / leads), canal


@pytest.mark.parametrize("periodo", PERIODOS)
def test_da_maior_conversao_para_a_menor(respostas, periodo):
    conversoes = [item["conversao"] for item in respostas[periodo].json()["canais"]]

    assert conversoes == sorted(conversoes, reverse=True)


def test_a_ordem_conhecida_troca_entre_12_meses_e_30_dias(respostas):
    """Não há mínimo de leads: em 30 dias, com base pequena, Indicação passa Mídia paga."""
    em_12_meses = [item["canal"] for item in respostas["12m"].json()["canais"]]
    em_30_dias = [item["canal"] for item in respostas["30d"].json()["canais"]]

    assert em_12_meses[:2] == ["Mídia paga", "Indicação"]
    assert em_30_dias.index("Indicação") < em_30_dias.index("Mídia paga")


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    inicio, fim = PERIODOS[periodo]

    assert respostas[periodo].json()["periodo"] == {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
    }


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.COMERCIAL))

    assert resposta.json() == respostas["12m"].json()


def test_resposta_tem_so_os_campos_do_contrato_e_nenhum_nome_interno(respostas):
    corpo = respostas["12m"].json()

    assert set(corpo) == {"periodo", "canais"}
    for item in corpo["canais"]:
        assert set(item) == CAMPOS_DO_CANAL
        assert isinstance(item["leads"], int)
        assert isinstance(item["novos_lojistas"], int)
    texto = respostas["12m"].text
    for proibido in ("email", "lojista_id", "pedido", "atras", "_id", "dados_de_origem", "origem"):
        assert proibido not in texto


def test_canal_sem_lead_e_canal_sem_fechamento_vem_vazios_no_fim_da_ordem(conexao_dono):
    """A consulta real, com o papel do Comercial, num período em que Eventos não tem lead criado
    e Orgânico não tem fechamento.

    Os dois casos só existem dentro de uma transação desfeita no fim: nenhum outro processo os
    vê, e os dados de origem ficam como estavam.
    """
    inicio, fim = PERIODOS["30d"]
    with conexao_dono.transaction(force_rollback=True):
        conexao_dono.execute(
            "update dados_de_origem.lead set data_criacao = %s"
            " where canal = 'Eventos' and data_criacao between %s and %s",
            (date(2024, 12, 1), inicio, fim),
        )
        conexao_dono.execute(
            "update dados_de_origem.lead"
            " set etapa = 'Perdido', data_fechamento = null, lojista_id = null"
            " where canal = 'Orgânico' and data_fechamento between %s and %s",
            (inicio, fim),
        )
        conexao_dono.execute("set local role comercial")
        canais = consultas_do_comercial.canais.ler(conexao_dono, Periodo.TRINTA_DIAS)["canais"]

    assert len(canais) == 5
    por_canal = {item["canal"]: item for item in canais}
    eventos_ = por_canal["Eventos"]
    assert (eventos_["leads"], eventos_["conversao"]) == (0, None)
    organico = por_canal["Orgânico"]
    assert organico["leads"] > 0
    assert (organico["novos_lojistas"], organico["conversao"]) == (0, 0)
    assert organico["dias_ate_fechar"] is None
    # O vazio vai para o fim, depois do canal de conversão zero.
    assert [item["canal"] for item in canais][-2:] == ["Orgânico", "Eventos"]


@pytest.fixture(scope="module")
def mcp(criar_mcp):
    return criar_mcp()


def test_a_ferramenta_aparece_so_para_o_comercial_e_recebe_so_o_periodo(mcp, token_de):
    quem_ve = {
        perfil
        for perfil in Perfil
        if FERRAMENTA in {f.name for f in listar_ferramentas(mcp, token_de(perfil))}
    }
    [publicada] = [
        f for f in listar_ferramentas(mcp, token_de(Perfil.COMERCIAL)) if f.name == FERRAMENTA
    ]

    assert quem_ve == {Perfil.COMERCIAL}
    assert set(publicada.input_schema["properties"]) == {"periodo"}


def test_a_descricao_diz_como_a_conversao_e_calculada(mcp, token_de):
    [publicada] = [
        f for f in listar_ferramentas(mcp, token_de(Perfil.COMERCIAL)) if f.name == FERRAMENTA
    ]
    descricao = publicada.description

    assert "novos lojistas do período ÷ leads criados no mesmo período" in descricao
    assert "não refaça a conta" in descricao
    assert "origem" not in descricao.lower()


def test_a_descricao_diz_o_tamanho_da_base_sem_ditar_a_resposta(mcp, token_de):
    """A descrição diz o que a ferramenta devolve; como responder fica com o assistente."""
    [publicada] = [
        f for f in listar_ferramentas(mcp, token_de(Perfil.COMERCIAL)) if f.name == FERRAMENTA
    ]
    descricao = publicada.description

    assert "'leads' e 'novos_lojistas' dão o tamanho da base de cada conversão" in descricao
    assert "ao responder" not in descricao.lower()
    assert "avise" not in descricao.lower()


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_conteudo_da_rota(mcp, respostas, token_de, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    resultado = chamar(mcp, token_de(Perfil.COMERCIAL), FERRAMENTA, {"periodo": periodo})

    assert not resultado.is_error
    assert resultado.structured_content == respostas[periodo].json()


def test_a_pergunta_sugerida_leva_os_canais_ao_modelo(
    criar_api, mcp_no_processo, token_de, respostas
):
    """Com o modelo roteirizado, a pergunta sugerida do Comercial chama `comercial_canais`, e o
    modelo recebe os canais já na ordem que responde à pergunta, sem conta própria."""
    vistos: dict = {}
    api = criar_api(
        modelo=modelo_roteirizado(chamadas=[(FERRAMENTA, {"periodo": "12m"})], vistos=vistos),
        endereco_do_mcp=mcp_no_processo + CAMINHO,
    )

    lidos = eventos(perguntar(api, token_de(Perfil.COMERCIAL), {"pergunta": PERGUNTA_SUGERIDA}))

    assert FERRAMENTA in vistos["ferramentas"]
    [chamada] = [dados for tipo, dados in lidos if tipo == "chamada"]
    assert chamada["ferramenta"] == FERRAMENTA
    assert chamada["desfecho"] == "concluida"
    [retorno] = [
        parte
        for mensagem in vistos["mensagens"]
        if isinstance(mensagem, ModelRequest)
        for parte in mensagem.parts
        if isinstance(parte, ToolReturnPart)
    ]
    assert retorno.tool_name == FERRAMENTA
    assert retorno.content == respostas["12m"].json()
    assert lidos[-1][0] == "fim"
