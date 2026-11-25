"""GET /produtos/avaliacoes e `produtos_avaliacoes`: as avaliações mais recentes, com o comentário.

O comentário é texto escrito por clientes, não confiável (RS-07, ADR 0010): a resposta traz um
aviso num campo próprio, ao lado das avaliações, e o texto chega sem filtro, cortado só num tamanho
máximo. Os valores esperados vêm dos dados de origem, lidos com o papel dono. O banco é o da carga
padrão (data de referência 30/11/2026).
"""

import os
from datetime import date

import httpx
import pytest
from apoio import ultima_chamada_de
from cliente_mcp import (
    MCP_DO_AMBIENTE,
    PARAMETRO_INVALIDO,
    chamar,
    listar_ferramentas,
    texto_do_erro,
)
from provedor import conteudo
from recusa import RESPOSTA_DE_PARAMETRO_INVALIDO, pedir

from acesso import Perfil

API_DO_AMBIENTE = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"
ROTA = "/produtos/avaliacoes"
FERRAMENTA = "produtos_avaliacoes"
LIMITE = 20
TAMANHO_MAXIMO_DO_COMENTARIO = 500

PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}
CAMPOS_DA_AVALIACAO = {"produto", "nome_do_produto", "categoria", "nota", "data", "comentario"}


def _na_origem(conexao, inicio: date, fim: date, produto: int | None = None) -> list[dict]:
    """As avaliações do período, da mais recente para a mais antiga, como a origem as tem."""
    linhas = conexao.execute(
        """
        select a.produto_id, p.nome, c.nome, a.nota, a.data_avaliacao, a.comentario
        from dados_de_origem.avaliacao a
        join dados_de_origem.produto p on p.id = a.produto_id
        join dados_de_origem.categoria c on c.id = p.categoria_id
        where a.data_avaliacao between %(inicio)s and %(fim)s
          and (%(produto)s::int is null or a.produto_id = %(produto)s::int)
        order by a.data_avaliacao desc, a.id desc
        limit %(limite)s
        """,
        {"inicio": inicio, "fim": fim, "produto": produto, "limite": LIMITE},
    ).fetchall()
    return [
        {
            "produto": produto_id,
            "nome_do_produto": nome,
            "categoria": categoria,
            "nota": nota,
            "data": data.isoformat(),
            "comentario": comentario,
        }
        for produto_id, nome, categoria, nota, data, comentario in linhas
    ]


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.PRODUTOS)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_rota_devolve_as_20_mais_recentes_do_periodo(respostas, conexao_dono, periodo):
    inicio, fim = PERIODOS[periodo]
    resposta = respostas[periodo]

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["periodo"] == {"inicio": inicio.isoformat(), "fim": fim.isoformat()}
    assert corpo["avaliacoes"] == _na_origem(conexao_dono, inicio, fim)
    assert len(corpo["avaliacoes"]) == LIMITE


def test_a_resposta_traz_o_aviso_de_que_os_comentarios_sao_texto_de_clientes(respostas):
    aviso = respostas["12m"].json()["aviso"].lower()

    assert "clientes" in aviso
    assert "instru" in aviso


def test_a_resposta_nao_traz_cliente_pedido_nem_lojista(respostas):
    corpo = respostas["24m"].json()

    assert set(corpo) == {"periodo", "aviso", "avaliacoes"}
    for avaliacao in corpo["avaliacoes"]:
        assert set(avaliacao) == CAMPOS_DA_AVALIACAO
    # O comentário é texto livre e pode falar de pedido; os nomes internos, não.
    texto = respostas["24m"].text
    for proibido in ("_id", "dados_de_origem", "produtos."):
        assert proibido not in texto


def test_a_avaliacao_sem_comentario_vem_sem_texto(respostas):
    avaliacoes = respostas["24m"].json()["avaliacoes"]

    sem_comentario = [a for a in avaliacoes if a["comentario"] is None]
    assert sem_comentario, "a carga padrão tem avaliações recentes sem comentário"


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.PRODUTOS))

    assert resposta.json() == respostas["12m"].json()


def test_a_rota_nao_aceita_o_produto(api, token_de):
    resposta = pedir(api, ROTA, token_de(Perfil.PRODUTOS), periodo="24m", produto="1")

    assert resposta.status_code == 400
    assert resposta.json() == RESPOSTA_DE_PARAMETRO_INVALIDO


# --- A ferramenta ---


def _assert_auditada(token: str, argumentos: dict, resultado: str) -> None:
    do_token = conteudo(token)
    linha = ultima_chamada_de(do_token["sub"])
    assert linha is not None
    assert linha["nome_do_usuario"] == do_token["name"]
    assert linha["perfil"] == "produtos"
    assert linha["ferramenta"] == FERRAMENTA
    assert linha["parametros"] == argumentos
    assert linha["resultado"] == resultado


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_sem_produto_devolve_o_mesmo_que_a_rota(token_de, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    token = token_de(Perfil.PRODUTOS)
    with httpx.Client(base_url=API_DO_AMBIENTE, timeout=10) as api:
        da_api = pedir(api, ROTA, token, periodo=periodo)

    resultado = chamar(MCP_DO_AMBIENTE, token, FERRAMENTA, {"periodo": periodo})

    assert da_api.status_code == 200
    assert not resultado.is_error
    assert resultado.structured_content == da_api.json()
    _assert_auditada(token, {"periodo": periodo}, "permitida")


@pytest.mark.parametrize(("produto", "periodo"), [(1, "24m"), (1, "12m"), (2, "24m")])
def test_com_produto_so_as_avaliacoes_dele_no_periodo(token_de, conexao_dono, produto, periodo):
    token = token_de(Perfil.PRODUTOS)
    argumentos = {"periodo": periodo, "produto": produto}

    resultado = chamar(MCP_DO_AMBIENTE, token, FERRAMENTA, argumentos)

    assert not resultado.is_error
    avaliacoes = resultado.structured_content["avaliacoes"]
    assert avaliacoes == _na_origem(conexao_dono, *PERIODOS[periodo], produto=produto)
    assert avaliacoes
    assert {a["produto"] for a in avaliacoes} == {produto}
    assert resultado.structured_content["aviso"]
    _assert_auditada(token, argumentos, "permitida")


def test_o_periodo_vale_tambem_com_produto(token_de):
    """O produto 1 tem a avaliação mais antiga em 10/12/2024: só os 24 meses a alcançam."""
    token = token_de(Perfil.PRODUTOS)

    em_24 = chamar(MCP_DO_AMBIENTE, token, FERRAMENTA, {"periodo": "24m", "produto": 1})
    em_12 = chamar(MCP_DO_AMBIENTE, token, FERRAMENTA, {"periodo": "12m", "produto": 1})

    datas_em_12 = {a["data"] for a in em_12.structured_content["avaliacoes"]}
    assert "2024-12-10" in {a["data"] for a in em_24.structured_content["avaliacoes"]}
    assert "2024-12-10" not in datas_em_12
    assert min(datas_em_12) >= PERIODOS["12m"][0].isoformat()


@pytest.mark.parametrize("produto", [2001, 2_147_483_647])
def test_produto_inexistente_devolve_lista_vazia(token_de, produto):
    token = token_de(Perfil.PRODUTOS)
    argumentos = {"periodo": "24m", "produto": produto}

    resultado = chamar(MCP_DO_AMBIENTE, token, FERRAMENTA, argumentos)

    assert not resultado.is_error
    assert resultado.structured_content["avaliacoes"] == []
    assert resultado.structured_content["aviso"]
    _assert_auditada(token, argumentos, "permitida")


@pytest.mark.parametrize(
    "argumentos",
    [
        {"produto": 0},
        {"produto": -1},
        {"produto": "1"},
        {"produto": "um"},
        {"produto": 1.5},
        {"produto": True},
        {"produto": None},
        {"produto": 2_147_483_648},
        {"produto": 1, "cliente": 1},
        {"periodo": "7d", "produto": 1},
    ],
    ids=str,
)
def test_produto_fora_do_tipo_ou_da_faixa_e_parametro_invalido(token_de, argumentos):
    token = token_de(Perfil.PRODUTOS)

    resultado = chamar(MCP_DO_AMBIENTE, token, FERRAMENTA, argumentos)

    assert texto_do_erro(resultado) == PARAMETRO_INVALIDO
    _assert_auditada(token, argumentos, "parametro_invalido")


def test_a_descricao_diz_que_os_comentarios_sao_texto_de_clientes_e_nao_instrucoes(token_de):
    [ferramenta] = [
        f
        for f in listar_ferramentas(MCP_DO_AMBIENTE, token_de(Perfil.PRODUTOS))
        if f.name == FERRAMENTA
    ]

    descricao = ferramenta.description.lower()
    assert "clientes" in descricao
    assert "não são instruções" in descricao


@pytest.fixture
def comentario_longo(conexao_dono):
    """Um comentário de 600 caracteres, posto por um instante numa avaliação do produto 2.

    O comentário original volta no fim. Só o texto muda: nenhuma contagem nem nota se altera.
    """
    id_da_avaliacao, original = conexao_dono.execute(
        """
        select id, comentario from dados_de_origem.avaliacao
        where produto_id = 2 and data_avaliacao >= %s
        order by data_avaliacao desc, id desc limit 1
        """,
        (PERIODOS["24m"][0],),
    ).fetchone()
    longo = "Texto longo de cliente. " * 25
    conexao_dono.execute(
        "update dados_de_origem.avaliacao set comentario = %s where id = %s",
        (longo, id_da_avaliacao),
    )
    try:
        yield longo
    finally:
        conexao_dono.execute(
            "update dados_de_origem.avaliacao set comentario = %s where id = %s",
            (original, id_da_avaliacao),
        )


def test_comentario_maior_que_500_caracteres_e_cortado(token_de, comentario_longo):
    token = token_de(Perfil.PRODUTOS)

    resultado = chamar(MCP_DO_AMBIENTE, token, FERRAMENTA, {"periodo": "24m", "produto": 2})

    primeiro = resultado.structured_content["avaliacoes"][0]
    assert len(comentario_longo) > TAMANHO_MAXIMO_DO_COMENTARIO
    assert primeiro["comentario"] == comentario_longo[:TAMANHO_MAXIMO_DO_COMENTARIO]
