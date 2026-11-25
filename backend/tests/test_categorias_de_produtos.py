"""GET /produtos/categorias: as 20 categorias com produtos, avaliações, nota média, reclamações e
taxa de reclamação do período, da pior nota média para a melhor.

Os valores esperados vêm de consultas independentes, feitas com o papel dono nos dados de origem:
o período filtra pela data da avaliação, e os produtos da categoria são os do catálogo, que não
depende do período (glossário). A ferramenta `produtos_categorias` devolve o mesmo conteúdo; ela é
chamada no servidor MCP criado dentro do processo.
"""

import threading
import time
from collections.abc import Iterator
from datetime import date

import pytest
import uvicorn
from cliente_mcp import CAMINHO, chamar
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from recusa import pedir
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil

ROTA = "/produtos/categorias"
FERRAMENTA = "produtos_categorias"
# A pergunta sugerida no painel do assistente de Produtos (frontend/src/perfis.ts).
PERGUNTA_SUGERIDA = "Quais categorias concentram as piores notas?"

PERIODOS = {
    "30d": (date(2026, 11, 1), date(2026, 11, 30)),
    "90d": (date(2026, 9, 2), date(2026, 11, 30)),
    "12m": (date(2025, 12, 1), date(2026, 11, 30)),
    "24m": (date(2024, 12, 1), date(2026, 11, 30)),
}

_NA_ORIGEM = """
select
    ca.nome,
    (select count(*) from dados_de_origem.produto p where p.categoria_id = ca.id),
    count(a.id),
    avg(a.nota),
    count(a.id) filter (where a.nota in (1, 2))
from dados_de_origem.categoria ca
left join dados_de_origem.produto pr on pr.categoria_id = ca.id
left join dados_de_origem.avaliacao a
    on a.produto_id = pr.id and a.data_avaliacao between %s and %s
group by ca.id, ca.nome
"""


def _na_origem(conexao, datas) -> dict[str, dict]:
    return {
        nome: {
            "produtos": produtos,
            "avaliacoes": avaliacoes,
            "nota_media": float(media),
            "reclamacoes": reclamacoes,
            "taxa_de_reclamacao": reclamacoes / avaliacoes,
        }
        for nome, produtos, avaliacoes, media, reclamacoes in conexao.execute(
            _NA_ORIGEM, datas
        ).fetchall()
    }


@pytest.fixture(scope="module")
def respostas(criar_api, token_de):
    api = criar_api()
    token = token_de(Perfil.PRODUTOS)
    return {periodo: pedir(api, ROTA, token, periodo=periodo) for periodo in PERIODOS}


@pytest.mark.parametrize("periodo", PERIODOS)
def test_as_20_categorias_batem_com_os_dados_de_origem(respostas, conexao_dono, periodo):
    resposta = respostas[periodo]
    na_origem = _na_origem(conexao_dono, PERIODOS[periodo])

    assert resposta.status_code == 200
    categorias = resposta.json()["categorias"]
    assert len(categorias) == 20
    assert {item["categoria"] for item in categorias} == set(na_origem)
    for item in categorias:
        nome = item["categoria"]
        esperado = na_origem[nome]
        assert item["produtos"] == esperado["produtos"], nome
        assert item["avaliacoes"] == esperado["avaliacoes"], nome
        assert item["reclamacoes"] == esperado["reclamacoes"], nome
        assert item["nota_media"] == pytest.approx(esperado["nota_media"]), nome
        assert item["taxa_de_reclamacao"] == pytest.approx(esperado["taxa_de_reclamacao"]), nome


@pytest.mark.parametrize("periodo", PERIODOS)
def test_da_pior_nota_media_para_a_melhor(respostas, periodo):
    medias = [item["nota_media"] for item in respostas[periodo].json()["categorias"]]

    assert medias == sorted(medias)


def test_os_produtos_da_categoria_somam_o_catalogo_em_qualquer_periodo(respostas):
    for resposta in respostas.values():
        assert sum(item["produtos"] for item in resposta.json()["categorias"]) == 2000


def test_nos_24_meses_as_faixas_sao_as_conhecidas(respostas):
    """Os números da spec #77: nota média de 3,92 a 4,27 e reclamações de 24 a 341."""
    categorias = respostas["24m"].json()["categorias"]

    assert round(categorias[0]["nota_media"], 2) == 3.92
    assert round(categorias[-1]["nota_media"], 2) == 4.27
    reclamacoes = [item["reclamacoes"] for item in categorias]
    assert (min(reclamacoes), max(reclamacoes)) == (24, 341)


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


def test_resposta_tem_so_os_campos_do_contrato_e_nenhum_nome_interno(respostas):
    corpo = respostas["12m"].json()

    assert set(corpo) == {"periodo", "categorias"}
    for item in corpo["categorias"]:
        assert set(item) == {
            "categoria",
            "produtos",
            "avaliacoes",
            "nota_media",
            "reclamacoes",
            "taxa_de_reclamacao",
        }
    texto = respostas["12m"].text
    for proibido in ("cliente", "pedido", "lojista", "_id", "dados_de_origem", "produtos."):
        assert proibido not in texto


@pytest.fixture(scope="module")
def mcp(criar_mcp):
    return criar_mcp()


@pytest.mark.parametrize("periodo", PERIODOS)
def test_a_ferramenta_devolve_o_mesmo_conteudo_da_rota(mcp, respostas, token_de, periodo):
    """Tela e agente nunca divergem: a mesma consulta, pelo mesmo mecanismo (RF-13)."""
    resultado = chamar(mcp, token_de(Perfil.PRODUTOS), FERRAMENTA, {"periodo": periodo})

    assert not resultado.is_error
    assert resultado.structured_content == respostas[periodo].json()


@pytest.fixture(scope="module")
def mcp_no_processo(criar_mcp) -> Iterator[str]:
    """O servidor MCP criado pela fábrica, servido numa thread: o assistente o chama pela rede,
    como chama o serviço `mcp` do compose, mas com as ferramentas deste código."""
    servidor = uvicorn.Server(
        uvicorn.Config(criar_mcp(), host="127.0.0.1", port=0, log_config=None, log_level="warning")
    )
    fio = threading.Thread(target=servidor.run, daemon=True)
    fio.start()
    limite = time.monotonic() + 30
    while not servidor.started:
        assert time.monotonic() < limite, "o servidor MCP não subiu"
        time.sleep(0.05)
    porta = servidor.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{porta}"
    servidor.should_exit = True
    fio.join(timeout=10)


def test_a_pergunta_sugerida_leva_as_categorias_ao_modelo(
    criar_api, mcp_no_processo, token_de, respostas
):
    """Com o modelo roteirizado, a pergunta sugerida de Produtos chama `produtos_categorias`, e o
    modelo recebe as categorias já na ordem que responde à pergunta, sem conta própria."""
    vistos: dict = {}
    api = criar_api(
        modelo=modelo_roteirizado(chamadas=[(FERRAMENTA, {"periodo": "12m"})], vistos=vistos),
        endereco_do_mcp=mcp_no_processo + CAMINHO,
    )

    lidos = eventos(perguntar(api, token_de(Perfil.PRODUTOS), {"pergunta": PERGUNTA_SUGERIDA}))

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
