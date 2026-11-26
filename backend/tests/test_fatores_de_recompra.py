"""GET /diretoria/fatores-de-recompra: os três blocos dos fatores de recompra, com o tamanho de
cada grupo.

Nos dois blocos de recompra, a conta é a taxa de recompra do cartão (dos clientes com pedido
aprovado no período, os que fizeram uma recompra nele), repartida por uma característica do
primeiro pedido aprovado do cliente, qualquer que seja a data dele: a entrega (no prazo ou com
atraso) e a nota que o cliente deu a ele (1 ou 2, 3, 4 ou 5). Os grupos sem desfecho ficam de
fora: o primeiro pedido em trânsito ou com prazo vencido, e o primeiro pedido sem avaliação. No
terceiro bloco, a satisfação das avaliações do período, conforme a entrega do pedido avaliado.

Os valores esperados vêm de consultas independentes, feitas com o papel dono nos dados de origem,
com a regra de data de Brasília (glossário). O banco é o da carga padrão (data de referência
30/11/2026). A ferramenta `diretoria_fatores_de_recompra` devolve o mesmo conteúdo, e a chamada
fica na auditoria com o usuário e o perfil da Diretoria.
"""

from datetime import date

import pytest
from auditada import assert_auditada
from cliente_mcp import CAMINHO, PARAMETRO_INVALIDO, chamar, listar_ferramentas, texto_do_erro
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from recusa import pedir
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil

ROTA = "/diretoria/fatores-de-recompra"
FERRAMENTA = "diretoria_fatores_de_recompra"
# A pergunta sugerida no painel do assistente da Diretoria (frontend/src/perfis.ts).
PERGUNTA_SUGERIDA = "Por que os clientes compram uma vez e não voltam?"

PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}

# Os grupos de cada bloco, na ordem em que a resposta os traz.
GRUPOS = {
    "primeira_entrega": ["No prazo", "Com atraso"],
    "primeira_nota": ["1 ou 2", "3", "4 ou 5"],
    "faixa_de_atraso": ["No prazo", "Até 7 dias", "Mais de 7 dias"],
}
BLOCOS_DE_RECOMPRA = ("primeira_entrega", "primeira_nota")
CAMPOS_DO_GRUPO_DE_RECOMPRA = {"grupo", "clientes", "clientes_com_recompra", "taxa_de_recompra"}
CAMPOS_DO_GRUPO_DE_SATISFACAO = {"grupo", "avaliacoes", "satisfacao"}

# Os valores dos dados atuais em 12 meses (spec #96): clientes com recompra e clientes do grupo.
CONHECIDOS_EM_12_MESES = {
    "primeira_entrega": {"No prazo": (1204, 13660), "Com atraso": (0, 1313)},
    "primeira_nota": {"1 ou 2": (10, 1258), "3": (107, 1044), "4 ou 5": (1087, 8408)},
}

# Os clientes com pedido aprovado no período, se fizeram recompra nele, e o primeiro pedido
# aprovado de cada um, com a entrega e a nota dele.
_CLIENTES_NA_ORIGEM = """
with aprovados as (
    select p.id, p.cliente_id,
           (p.momento_compra at time zone 'America/Sao_Paulo')::date as dia,
           row_number() over (partition by p.cliente_id order by p.momento_compra, p.id) as ordem
    from dados_de_origem.pedido p
    join dados_de_origem.pagamento g on g.pedido_id = p.id
    where g.situacao = 'Aprovado'
),
do_periodo as (
    select cliente_id, bool_or(ordem > 1) as recompra
    from aprovados where dia between %(inicio)s and %(fim)s
    group by cliente_id
)
select d.recompra, e.situacao, v.nota
from do_periodo d
join aprovados primeiro on primeiro.cliente_id = d.cliente_id and primeiro.ordem = 1
left join dados_de_origem.entrega e on e.pedido_id = primeiro.id
left join dados_de_origem.avaliacao v on v.pedido_id = primeiro.id
"""

_AVALIACOES_NA_ORIGEM = """
select e.data_prometida, e.data_entrega, v.nota
from dados_de_origem.avaliacao v
join dados_de_origem.entrega e on e.pedido_id = v.pedido_id
where v.data_avaliacao between %(inicio)s and %(fim)s
"""


def _grupo_da_entrega(situacao: str | None) -> str | None:
    return {"Entregue no prazo": "No prazo", "Entregue com atraso": "Com atraso"}.get(situacao)


def _grupo_da_nota(nota: int | None) -> str | None:
    if nota is None:
        return None
    return "1 ou 2" if nota <= 2 else "3" if nota == 3 else "4 ou 5"


def _faixa(prometida: date, entrega: date | None) -> str | None:
    if entrega is None:
        return None
    dias = (entrega - prometida).days
    return "No prazo" if dias <= 0 else "Até 7 dias" if dias <= 7 else "Mais de 7 dias"


def _na_origem(conexao, datas) -> dict[str, dict[str, tuple]]:
    """Por bloco e grupo: (clientes com recompra, clientes) ou (soma das notas, avaliações)."""
    inicio, fim = datas
    contas: dict[str, dict[str, list[int]]] = {
        bloco: {grupo: [0, 0] for grupo in grupos} for bloco, grupos in GRUPOS.items()
    }
    for recompra, situacao, nota in conexao.execute(
        _CLIENTES_NA_ORIGEM, {"inicio": inicio, "fim": fim}
    ):
        for bloco, grupo in (
            ("primeira_entrega", _grupo_da_entrega(situacao)),
            ("primeira_nota", _grupo_da_nota(nota)),
        ):
            if grupo is not None:
                contas[bloco][grupo][0] += int(recompra)
                contas[bloco][grupo][1] += 1
    for prometida, entrega, nota in conexao.execute(
        _AVALIACOES_NA_ORIGEM, {"inicio": inicio, "fim": fim}
    ):
        faixa = _faixa(prometida, entrega)
        if faixa is not None:
            contas["faixa_de_atraso"][faixa][0] += nota
            contas["faixa_de_atraso"][faixa][1] += 1
    return {
        bloco: {grupo: tuple(par) for grupo, par in grupos.items()}
        for bloco, grupos in contas.items()
    }


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.DIRETORIA)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    inicio, fim = PERIODOS[periodo]
    resposta = respostas[periodo]

    assert resposta.status_code == 200
    assert resposta.json()["periodo"] == {"inicio": inicio.isoformat(), "fim": fim.isoformat()}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_os_tres_blocos_trazem_os_grupos_da_enumeracao_na_ordem(respostas, periodo):
    corpo = respostas[periodo].json()

    assert set(corpo) == {"periodo", *GRUPOS}
    for bloco, grupos in GRUPOS.items():
        assert [item["grupo"] for item in corpo[bloco]] == grupos, bloco


@pytest.mark.parametrize("periodo", PERIODOS)
def test_os_blocos_de_recompra_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    corpo = respostas[periodo].json()
    na_origem = _na_origem(conexao_dono, PERIODOS[periodo])

    for bloco in BLOCOS_DE_RECOMPRA:
        for item in corpo[bloco]:
            com_recompra, clientes = na_origem[bloco][item["grupo"]]
            assert set(item) == CAMPOS_DO_GRUPO_DE_RECOMPRA
            assert (item["clientes_com_recompra"], item["clientes"]) == (com_recompra, clientes)
            assert item["taxa_de_recompra"] == pytest.approx(com_recompra / clientes)


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_satisfacao_por_faixa_de_atraso_bate_com_os_dados_de_origem(
    respostas, conexao_dono, periodo
):
    corpo = respostas[periodo].json()
    na_origem = _na_origem(conexao_dono, PERIODOS[periodo])["faixa_de_atraso"]

    for item in corpo["faixa_de_atraso"]:
        soma, avaliacoes = na_origem[item["grupo"]]
        assert set(item) == CAMPOS_DO_GRUPO_DE_SATISFACAO
        assert item["avaliacoes"] == avaliacoes
        assert item["satisfacao"] == pytest.approx(soma / avaliacoes)


def test_os_valores_conhecidos_dos_dados_atuais_em_12_meses(respostas):
    corpo = respostas["12m"].json()

    for bloco, grupos in CONHECIDOS_EM_12_MESES.items():
        por_grupo = {item["grupo"]: item for item in corpo[bloco]}
        for grupo, (com_recompra, clientes) in grupos.items():
            item = por_grupo[grupo]
            assert (item["clientes_com_recompra"], item["clientes"]) == (com_recompra, clientes)
            assert item["taxa_de_recompra"] == pytest.approx(com_recompra / clientes)


def test_em_12_meses_o_atraso_derruba_a_nota(respostas):
    """O terceiro elo da cadeia: quanto maior o atraso, menor a satisfação."""
    satisfacao = [item["satisfacao"] for item in respostas["12m"].json()["faixa_de_atraso"]]

    assert satisfacao == sorted(satisfacao, reverse=True)


@pytest.mark.parametrize("periodo", PERIODOS)
def test_os_grupos_de_recompra_nao_passam_do_total_do_cartao(api, token_de, respostas, periodo):
    corpo = respostas[periodo].json()
    cartao = pedir(api, "/diretoria/indicadores", token_de(Perfil.DIRETORIA), periodo=periodo)
    recompra = cartao.json()["taxa_de_recompra"]

    for bloco in BLOCOS_DE_RECOMPRA:
        assert sum(item["clientes"] for item in corpo[bloco]) <= recompra["clientes"], bloco
        assert (
            sum(item["clientes_com_recompra"] for item in corpo[bloco])
            <= recompra["clientes_com_recompra"]
        ), bloco


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.DIRETORIA))

    assert resposta.json() == respostas["12m"].json()


@pytest.mark.parametrize("periodo", ["7d", "", "12M", "todos"])
def test_periodo_fora_da_enumeracao_e_parametro_invalido(api, token_de, periodo):
    resposta = pedir(api, ROTA, token_de(Perfil.DIRETORIA), periodo=periodo)

    assert resposta.status_code == 400


def test_resposta_tem_numeros_crus_e_nenhum_nome_interno(respostas):
    texto = respostas["30d"].text

    for proibido in (
        "_id",
        "contagem",
        "dados_de_origem",
        "base_da_diretoria",
        "Sem avaliação",
        "Em trânsito",
        "Prazo vencido",
    ):
        assert proibido not in texto


@pytest.fixture(scope="module")
def mcp(criar_mcp):
    return criar_mcp()


def _publicada(mcp, token_de):
    [publicada] = [
        f for f in listar_ferramentas(mcp, token_de(Perfil.DIRETORIA)) if f.name == FERRAMENTA
    ]
    return publicada


def test_a_ferramenta_aparece_so_para_a_diretoria_e_recebe_so_o_periodo(mcp, token_de):
    quem_ve = {
        perfil
        for perfil in Perfil
        if FERRAMENTA in {f.name for f in listar_ferramentas(mcp, token_de(perfil))}
    }

    assert quem_ve == {Perfil.DIRETORIA}
    assert set(_publicada(mcp, token_de).input_schema["properties"]) == {"periodo"}


def test_a_descricao_diz_como_a_conta_e_feita_e_quais_grupos_ficam_de_fora(mcp, token_de):
    descricao = _publicada(mcp, token_de).description

    assert "primeiro pedido aprovado do cliente" in descricao
    assert "não refaça a conta" in descricao
    assert "em trânsito ou com prazo vencido ficam de fora" in descricao
    assert "não avaliaram o primeiro pedido ficam de fora" in descricao
    assert "não tire conclusão" in descricao


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_conteudo_da_rota_e_fica_na_auditoria(
    mcp, respostas, token_de, periodo
):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    token = token_de(Perfil.DIRETORIA)

    resultado = chamar(mcp, token, FERRAMENTA, {"periodo": periodo})

    assert not resultado.is_error
    assert resultado.structured_content == respostas[periodo].json()
    assert_auditada(token, FERRAMENTA, {"periodo": periodo}, "permitida")


def test_sem_periodo_a_ferramenta_devolve_os_12_meses(mcp, respostas, token_de):
    resultado = chamar(mcp, token_de(Perfil.DIRETORIA), FERRAMENTA, {})

    assert not resultado.is_error
    assert resultado.structured_content == respostas["12m"].json()


@pytest.mark.parametrize(
    "argumentos",
    [
        {"periodo": "7d"},
        {"periodo": None},
        {"periodo": 30},
        {"periodo": "30d", "bloco": "primeira_nota"},
        {"periodo": "30d", "cliente": 1},
    ],
    ids=str,
)
def test_parametro_fora_da_enumeracao_e_campo_extra_sao_parametro_invalido(
    mcp, token_de, argumentos
):
    token = token_de(Perfil.DIRETORIA)

    resultado = chamar(mcp, token, FERRAMENTA, argumentos)

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO
    assert_auditada(token, FERRAMENTA, argumentos, "parametro_invalido")


def test_a_pergunta_sugerida_leva_os_tres_blocos_ao_modelo(
    criar_api, mcp_no_processo, token_de, respostas
):
    """Com o modelo roteirizado, a pergunta sugerida da Diretoria chama
    `diretoria_fatores_de_recompra` com o token da Diretoria: o rastreio mostra a chamada, a
    auditoria a registra, e o modelo recebe os três blocos numa chamada só."""
    vistos: dict = {}
    api = criar_api(
        modelo=modelo_roteirizado(chamadas=[(FERRAMENTA, {"periodo": "12m"})], vistos=vistos),
        endereco_do_mcp=mcp_no_processo + CAMINHO,
    )
    token = token_de(Perfil.DIRETORIA)

    lidos = eventos(perguntar(api, token, {"pergunta": PERGUNTA_SUGERIDA}))

    assert FERRAMENTA in vistos["ferramentas"]
    [chamada] = [dados for tipo, dados in lidos if tipo == "chamada"]
    assert chamada["ferramenta"] == FERRAMENTA
    assert chamada["desfecho"] == "concluida"
    assert_auditada(token, FERRAMENTA, {"periodo": "12m"}, "permitida")
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
