"""GET /diretoria/resumo: o resumo por canal do lojista, do canal com maior taxa de atraso para o
de menor.

O canal é o do lead que originou o lojista. Os valores esperados vêm de consultas independentes,
feitas com o papel dono nos dados de origem, com as regras dos outros perfis: o pedido entra no
período pelo dia da compra no horário de Brasília, como em Vendas, e a avaliação pela data dela,
como em Produtos; na taxa de recompra, o cliente conta no canal do lojista do primeiro pedido
aprovado dele (glossário, spec #96). O banco é o da carga padrão (data de referência 30/11/2026).
A ferramenta `diretoria_resumo` devolve o mesmo conteúdo; ela é chamada no servidor MCP criado
dentro do processo.
"""

from datetime import date

import pytest
from cliente_mcp import PARAMETRO_INVALIDO, chamar, listar_ferramentas, texto_do_erro
from recusa import pedir

from acesso import Perfil
from consultas import diretoria as consultas_da_diretoria
from consultas.periodo import Periodo

ROTA = "/diretoria/resumo"
FERRAMENTA = "diretoria_resumo"

# Os canais do glossário.
CANAIS = {"Indicação", "Orgânico", "Mídia paga", "Eventos", "Prospecção ativa"}
PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}
CAMPOS_DO_CANAL = {
    "canal",
    "pedidos",
    "receita",
    "taxa_de_atraso",
    "entregues",
    "atrasos",
    "satisfacao",
    "avaliacoes",
    "taxa_de_recompra",
    "clientes",
    "clientes_com_recompra",
}

# Cada lojista no canal do lead que o originou.
_CANAL_DO_LOJISTA = """
    canal_do_lojista as (
        select lojista_id, canal from dados_de_origem.lead where lojista_id is not null
    )
"""

_PEDIDOS_NA_ORIGEM = f"""
with {_CANAL_DO_LOJISTA}
select
    c.canal,
    count(*),
    coalesce(sum(g.valor) filter (where g.situacao = 'Aprovado'), 0),
    count(*) filter (where e.situacao like 'Entregue%%'),
    count(*) filter (where e.situacao = 'Entregue com atraso')
from dados_de_origem.pedido p
join canal_do_lojista c using (lojista_id)
join dados_de_origem.pagamento g on g.pedido_id = p.id
left join dados_de_origem.entrega e on e.pedido_id = p.id
where (p.momento_compra at time zone 'America/Sao_Paulo')::date between %(inicio)s and %(fim)s
group by c.canal
"""

_AVALIACOES_NA_ORIGEM = f"""
with {_CANAL_DO_LOJISTA}
select c.canal, count(*), avg(v.nota)
from dados_de_origem.avaliacao v
join dados_de_origem.pedido p on p.id = v.pedido_id
join canal_do_lojista c using (lojista_id)
where v.data_avaliacao between %(inicio)s and %(fim)s
group by c.canal
"""

# Os pedidos aprovados, numerados na ordem das compras do cliente: o primeiro dá o canal do
# cliente, e os demais são recompras.
_CLIENTES_NA_ORIGEM = f"""
with {_CANAL_DO_LOJISTA},
aprovados as (
    select p.cliente_id, p.lojista_id,
           (p.momento_compra at time zone 'America/Sao_Paulo')::date as dia,
           row_number() over (partition by p.cliente_id order by p.momento_compra, p.id) as ordem
    from dados_de_origem.pedido p
    join dados_de_origem.pagamento g on g.pedido_id = p.id
    where g.situacao = 'Aprovado'
),
canal_do_cliente as (
    select a.cliente_id, c.canal
    from aprovados a join canal_do_lojista c using (lojista_id)
    where a.ordem = 1
)
select k.canal, count(distinct a.cliente_id),
       count(distinct a.cliente_id) filter (where a.ordem > 1)
from aprovados a
join canal_do_cliente k using (cliente_id)
where a.dia between %(inicio)s and %(fim)s
group by k.canal
"""


def _razao(parte, todo):
    return parte / todo if todo else None


def _na_origem(conexao, datas) -> dict[str, dict]:
    inicio, fim = datas
    parametros = {"inicio": inicio, "fim": fim}
    esperado = {
        canal: {
            "pedidos": 0,
            "receita": 0.0,
            "entregues": 0,
            "atrasos": 0,
            "avaliacoes": 0,
            "satisfacao": None,
            "clientes": 0,
            "clientes_com_recompra": 0,
        }
        for canal in CANAIS
    }
    for canal, pedidos, receita, entregues, atrasos in conexao.execute(
        _PEDIDOS_NA_ORIGEM, parametros
    ):
        esperado[canal].update(
            pedidos=pedidos, receita=float(receita), entregues=entregues, atrasos=atrasos
        )
    for canal, avaliacoes, media in conexao.execute(_AVALIACOES_NA_ORIGEM, parametros):
        esperado[canal].update(avaliacoes=avaliacoes, satisfacao=float(media))
    for canal, clientes, com_recompra in conexao.execute(_CLIENTES_NA_ORIGEM, parametros):
        esperado[canal].update(clientes=clientes, clientes_com_recompra=com_recompra)
    for item in esperado.values():
        item["taxa_de_atraso"] = _razao(item["atrasos"], item["entregues"])
        item["taxa_de_recompra"] = _razao(item["clientes_com_recompra"], item["clientes"])
    return esperado


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.DIRETORIA)
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
        esperado = na_origem[item["canal"]]
        for campo, valor in esperado.items():
            assert item[campo] == pytest.approx(valor), f"{item['canal']}.{campo}"


def _taxa_de_atraso_ou_menos_um(item) -> float:
    return -1 if item["taxa_de_atraso"] is None else item["taxa_de_atraso"]


@pytest.mark.parametrize("periodo", PERIODOS)
def test_da_maior_taxa_de_atraso_para_a_menor(respostas, periodo):
    taxas = [_taxa_de_atraso_ou_menos_um(item) for item in respostas[periodo].json()["canais"]]

    assert taxas == sorted(taxas, reverse=True)


@pytest.mark.parametrize("periodo", ["12m", "24m"])
def test_em_12_e_24_meses_midia_paga_e_o_canal_que_mais_atrasa(respostas, periodo):
    assert respostas[periodo].json()["canais"][0]["canal"] == "Mídia paga"


@pytest.mark.parametrize("periodo", PERIODOS)
def test_os_canais_somam_o_total_dos_cartoes_no_mesmo_periodo(api, token_de, respostas, periodo):
    """Cada pedido, avaliação e cliente conta num canal só: a soma dos canais é o total."""
    canais = respostas[periodo].json()["canais"]
    cartao = pedir(api, "/diretoria/indicadores", token_de(Perfil.DIRETORIA), periodo=periodo)
    de_vendas = pedir(api, "/vendas/indicadores", token_de(Perfil.VENDAS), periodo=periodo)
    cartao, de_vendas = cartao.json(), de_vendas.json()

    def soma(campo):
        return sum(item[campo] for item in canais)

    assert soma("receita") == pytest.approx(cartao["receita"]["atual"])
    assert soma("pedidos") == de_vendas["pedidos_realizados"]["atual"]
    assert soma("atrasos") == de_vendas["taxa_de_atraso"]["atrasos"]
    assert soma("atrasos") / soma("entregues") == pytest.approx(
        de_vendas["taxa_de_atraso"]["atual"]
    )
    assert soma("avaliacoes") == cartao["satisfacao"]["avaliacoes"]
    assert soma("clientes") == cartao["taxa_de_recompra"]["clientes"]
    assert soma("clientes_com_recompra") == cartao["taxa_de_recompra"]["clientes_com_recompra"]


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    inicio, fim = PERIODOS[periodo]

    assert respostas[periodo].json()["periodo"] == {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
    }


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.DIRETORIA))

    assert resposta.json() == respostas["12m"].json()


@pytest.mark.parametrize(
    "parametros",
    [{"periodo": "7d"}, {"periodo": ""}, {"periodo": "30d", "canal": "Mídia paga"}],
    ids=str,
)
def test_periodo_invalido_e_campo_de_dimensao_sao_parametro_invalido(api, token_de, parametros):
    resposta = pedir(api, ROTA, token_de(Perfil.DIRETORIA), **parametros)

    assert resposta.status_code == 400


def test_resposta_tem_so_os_campos_do_contrato_e_nenhum_nome_interno(respostas):
    corpo = respostas["12m"].json()

    assert set(corpo) == {"periodo", "canais"}
    for item in corpo["canais"]:
        assert set(item) == CAMPOS_DO_CANAL
        for contagem in ("pedidos", "entregues", "atrasos", "avaliacoes", "clientes"):
            assert isinstance(item[contagem], int), contagem
    texto = respostas["12m"].text
    for proibido in ("lojista", "_id", "origem", "contagem", "base_da_diretoria"):
        assert proibido not in texto


# Os pedidos dos lojistas de um canal, nos dados de origem.
_PEDIDOS_DO_CANAL = """
    select p.id from dados_de_origem.pedido p
    join dados_de_origem.lead l on l.lojista_id = p.lojista_id
    where l.canal = %s
"""


def test_canal_sem_entrega_e_canal_sem_avaliacao_vem_com_a_taxa_vazia(conexao_dono):
    """A consulta real, com o papel da Diretoria, num período em que nenhum pedido de Eventos foi
    entregue e nenhuma avaliação de Orgânico foi feita.

    Os dois casos só existem dentro de uma transação desfeita no fim: nenhum outro processo os
    vê, e os dados de origem ficam como estavam.
    """
    inicio, fim = PERIODOS["30d"]
    with conexao_dono.transaction(force_rollback=True):
        conexao_dono.execute(
            "update dados_de_origem.entrega set situacao = 'Em trânsito', data_entrega = null"
            f" where pedido_id in ({_PEDIDOS_DO_CANAL})"
            "   and pedido_id in (select id from dados_de_origem.pedido"
            "       where (momento_compra at time zone 'America/Sao_Paulo')::date"
            "           between %s and %s)",
            ("Eventos", inicio, fim),
        )
        conexao_dono.execute(
            "delete from dados_de_origem.avaliacao"
            f" where pedido_id in ({_PEDIDOS_DO_CANAL}) and data_avaliacao between %s and %s",
            ("Orgânico", inicio, fim),
        )
        conexao_dono.execute("set local role diretoria")
        canais = consultas_da_diretoria.resumo.ler(conexao_dono, Periodo.TRINTA_DIAS)["canais"]

    assert len(canais) == 5
    por_canal = {item["canal"]: item for item in canais}
    eventos = por_canal["Eventos"]
    assert eventos["pedidos"] > 0
    assert (eventos["entregues"], eventos["atrasos"], eventos["taxa_de_atraso"]) == (0, 0, None)
    assert eventos["taxa_de_recompra"] is not None
    organico = por_canal["Orgânico"]
    assert (organico["avaliacoes"], organico["satisfacao"]) == (0, None)
    assert organico["taxa_de_atraso"] is not None
    assert organico["pedidos"] > 0
    # O canal sem taxa de atraso vai para o fim, e a linha dele continua inteira.
    assert canais[-1]["canal"] == "Eventos"
    assert set(eventos) == CAMPOS_DO_CANAL


# --- A ferramenta ---


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


def test_a_descricao_diz_como_o_cliente_e_contado_no_canal(mcp, token_de):
    descricao = _publicada(mcp, token_de).description

    assert "no canal do lojista do primeiro pedido aprovado dele" in descricao
    assert "do lead que originou o lojista" in descricao
    assert "não refaça a conta" in descricao
    assert "origem" not in descricao.lower()


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_conteudo_da_rota(mcp, respostas, token_de, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    resultado = chamar(mcp, token_de(Perfil.DIRETORIA), FERRAMENTA, {"periodo": periodo})

    assert not resultado.is_error
    assert resultado.structured_content == respostas[periodo].json()


def test_sem_periodo_a_ferramenta_devolve_os_12_meses(mcp, token_de, respostas):
    resultado = chamar(mcp, token_de(Perfil.DIRETORIA), FERRAMENTA, {})

    assert not resultado.is_error
    assert resultado.structured_content == respostas["12m"].json()


@pytest.mark.parametrize(
    "argumentos",
    [
        {"periodo": "7d"},
        {"periodo": ""},
        {"periodo": None},
        {"periodo": ["30d"]},
        {"periodo": "30d", "canal": "Mídia paga"},
        {"periodo": "30d", "lojista": 1},
        {"periodo": "30d", "categoria": "Eletrônicos"},
    ],
    ids=str,
)
def test_periodo_invalido_e_campo_de_dimensao_sao_parametro_invalido_na_ferramenta(
    mcp, token_de, argumentos
):
    resultado = chamar(mcp, token_de(Perfil.DIRETORIA), FERRAMENTA, argumentos)

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO
