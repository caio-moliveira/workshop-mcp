"""GET /produtos/mal-avaliados: os produtos mal avaliados do período, do pior para o melhor.

Produto mal avaliado (glossário): nota média abaixo de 3,0 nas avaliações do período, com pelo
menos 3 avaliações no período. As linhas esperadas vêm de uma consulta independente, feita com o
papel dono nos dados de origem. O banco é o da carga padrão (data de referência 30/11/2026).
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from apoio import ultima_chamada_de
from chaves_locais import ChavesLocais, assinar, conteudo_valido, nova_chave
from cliente_mcp import chamar
from provedor import DESTINATARIO_DO_MCP
from recusa import pedir

from acesso import Perfil

ROTA = "/produtos/mal-avaliados"
FERRAMENTA = "produtos_mal_avaliados"
CHAVE = nova_chave()

PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}
# Produtos mal avaliados com os dados atuais (spec #77), contados à parte nos dados de origem.
MAL_AVALIADOS_CONHECIDOS = {"30d": 4, "90d": 26, "12m": 20, "24m": 7}
LIMITE = 50

CAMPOS = {"produto", "nome_do_produto", "categoria", "preco", "nota_media", "avaliacoes"}

_NA_ORIGEM = """
select p.id, p.nome, c.nome, p.preco, avg(a.nota), count(*)
from dados_de_origem.avaliacao a
join dados_de_origem.produto p on p.id = a.produto_id
join dados_de_origem.categoria c on c.id = p.categoria_id
where a.data_avaliacao between %s and %s
group by p.id, p.nome, c.nome, p.preco
having avg(a.nota) < 3 and count(*) >= 3
order by avg(a.nota), count(*) desc, p.id
"""


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.PRODUTOS)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


def _como_linha(produto: dict) -> tuple:
    return (
        produto["produto"],
        produto["nome_do_produto"],
        produto["categoria"],
        Decimal(str(produto["preco"])),
        produto["nota_media"],
        produto["avaliacoes"],
    )


@pytest.mark.parametrize("periodo", PERIODOS)
def test_produtos_batem_com_os_dados_de_origem_do_pior_para_o_melhor(
    respostas, conexao_dono, periodo
):
    resposta = respostas[periodo]
    esperado = conexao_dono.execute(_NA_ORIGEM, PERIODOS[periodo]).fetchall()

    assert resposta.status_code == 200
    produtos = resposta.json()["produtos"]
    assert all(set(p) == CAMPOS for p in produtos)
    linhas = [_como_linha(p) for p in produtos]
    assert [(i, n, c, p, q) for i, n, c, p, _, q in linhas] == [
        (i, n, c, p, q) for i, n, c, p, _, q in esperado
    ]
    assert [m for *_, m, _ in linhas] == pytest.approx([float(m) for *_, m, _ in esperado])
    medias = [p["nota_media"] for p in produtos]
    assert medias == sorted(medias)


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_quantidade_bate_com_o_indicador_do_mesmo_periodo_e_respeita_o_teto(
    api, token_de, respostas, periodo
):
    """A lista e o cartão de produtos mal avaliados nunca divergem."""
    indicadores = pedir(api, "/produtos/indicadores", token_de(Perfil.PRODUTOS), periodo=periodo)
    produtos = respostas[periodo].json()["produtos"]

    assert len(produtos) == MAL_AVALIADOS_CONHECIDOS[periodo]
    assert len(produtos) == indicadores.json()["produtos_mal_avaliados"]["atual"]
    assert len(produtos) <= LIMITE


def test_produto_com_menos_de_3_avaliacoes_nao_aparece_mesmo_com_media_baixa(
    respostas, conexao_dono
):
    com_poucas = conexao_dono.execute(
        """
        select produto_id from dados_de_origem.avaliacao
        where data_avaliacao between %s and %s
        group by produto_id having avg(nota) < 3 and count(*) < 3
        """,
        PERIODOS["30d"],
    ).fetchall()
    produtos = respostas["30d"].json()["produtos"]

    assert com_poucas
    assert {p["produto"] for p in produtos}.isdisjoint({produto for (produto,) in com_poucas})
    assert all(p["avaliacoes"] >= 3 for p in produtos)


@pytest.mark.parametrize("periodo", PERIODOS)
def test_periodo_efetivo_termina_na_data_de_referencia(respostas, periodo):
    inicio, fim = PERIODOS[periodo]

    assert respostas[periodo].json()["periodo"] == {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
    }


def test_sem_periodo_vale_o_de_12_meses(api, token_de, respostas):
    resposta = pedir(api, ROTA, token_de(Perfil.PRODUTOS))

    assert resposta.json() == respostas["12m"].json()


def test_resposta_tem_numeros_crus_e_nenhum_nome_interno(respostas):
    corpo = respostas["12m"].json()

    assert set(corpo) == {"periodo", "produtos"}
    for produto in corpo["produtos"]:
        assert isinstance(produto["produto"], int)
        assert isinstance(produto["avaliacoes"], int)
        assert 1 <= produto["nota_media"] < 3
        assert produto["preco"] > 0
    texto = respostas["12m"].text
    for proibido in ("cliente", "pedido", "lojista", "_id", "dados_de_origem", "produtos."):
        assert proibido not in texto


@pytest.fixture(scope="module")
def mcp(criar_mcp):
    """O servidor MCP criado no processo, com o código desta branch."""
    return criar_mcp(chaves=ChavesLocais(CHAVE))


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_que_a_rota_e_fica_na_auditoria(mcp, respostas, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    sub = str(uuid.uuid4())
    token = assinar(
        conteudo_valido(aud=DESTINATARIO_DO_MCP, perfil=Perfil.PRODUTOS.value, sub=sub), CHAVE
    )

    resultado = chamar(mcp, token, FERRAMENTA, {"periodo": periodo})

    assert not resultado.is_error
    assert resultado.structured_content == respostas[periodo].json()
    linha = ultima_chamada_de(sub)
    assert linha is not None
    assert linha["perfil"] == "produtos"
    assert linha["ferramenta"] == FERRAMENTA
    assert linha["parametros"] == {"periodo": periodo}
    assert linha["resultado"] == "permitida"
