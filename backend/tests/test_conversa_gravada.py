"""A conversa gravada no histórico e continuada pelo servidor (RF-18, ADR 0009).

A API é criada dentro do processo, com um modelo roteirizado. O resto é de verdade: o token do
provedor do compose, o serviço `mcp` do compose e o banco `historico` do compose.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import replace

import pytest
from apoio import banco_local, variavel
from provedor import conteudo
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from roteiro import ROTA, eventos, modelo_roteirizado, perguntar

from acesso import Perfil, mensagens
from assistente import Limites
from consultas import Credencial
from historico import PAPEL, HistoricoIndisponivel, HistoricoNoBanco

PERGUNTA = "O que está causando os atrasos?"
CONVERSA_INEXISTENTE = {"erro": mensagens.CONVERSA_INEXISTENTE}
# O que a recusa de uma conversa não pode citar: banco, papel, tabela nem o identificador pedido.
NOMES_INTERNOS = ["historico", "postgres", "psycopg", "conversa.id", "select"]


def _identificadores(lidos) -> tuple[str, str]:
    tipo, dados = lidos[0]
    assert tipo == "conversa"
    return dados["id_da_conversa"], dados["id_da_pergunta"]


def ler_conversa(api, token: str | None, id_da_conversa: str):
    cabecalhos = {"Authorization": f"Bearer {token}"} if token else {}
    return api.get(f"/conversas/{id_da_conversa}", headers=cabecalhos)


def _conversa_recebida(mensagens_do_modelo: list[ModelMessage]) -> list[tuple[str, str]]:
    """As perguntas e respostas que o modelo recebeu, em ordem, como (autor, texto)."""
    itens = []
    for mensagem in mensagens_do_modelo:
        for parte in mensagem.parts:
            if isinstance(mensagem, ModelRequest) and isinstance(parte, UserPromptPart):
                itens.append(("usuario", parte.content))
            elif isinstance(mensagem, ModelResponse) and isinstance(parte, TextPart):
                itens.append(("assistente", parte.content))
    return itens


def _assert_conversa_inexistente(resposta) -> None:
    assert resposta.status_code == 404
    assert resposta.json() == CONVERSA_INEXISTENTE
    assert not [nome for nome in NOMES_INTERNOS if nome in resposta.text.lower()]


@pytest.fixture
def com_roteiro(criar_api):
    def criar(**roteiro):
        return criar_api(modelo=modelo_roteirizado(**roteiro))

    return criar


def test_a_pergunta_sem_conversa_cria_uma_e_o_fluxo_abre_com_os_identificadores(
    com_roteiro, token_de
):
    lidos = eventos(perguntar(com_roteiro(), token_de(Perfil.VENDAS), {"pergunta": PERGUNTA}))

    id_da_conversa, id_da_pergunta = _identificadores(lidos)
    assert uuid.UUID(id_da_conversa) != uuid.UUID(id_da_pergunta)
    assert [tipo for tipo, _ in lidos].count("conversa") == 1
    assert lidos[-1][0] == "fim"


def test_a_conversa_lida_depois_traz_a_pergunta_a_resposta_e_a_situacao(com_roteiro, token_de):
    token = token_de(Perfil.VENDAS)
    lidos = eventos(
        perguntar(com_roteiro(pedacos=["Três ", "lojistas."]), token, {"pergunta": PERGUNTA})
    )
    id_da_conversa, id_da_pergunta = _identificadores(lidos)

    resposta = ler_conversa(com_roteiro(), token, id_da_conversa)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": id_da_conversa,
        "titulo": PERGUNTA,
        "itens": [
            {"autor": "usuario", "texto": PERGUNTA},
            {
                "autor": "assistente",
                "texto": "Três lojistas.",
                "situacao": "concluida",
                "id_da_pergunta": id_da_pergunta,
                "rastreio": [],
            },
        ],
    }


def test_o_titulo_e_o_comeco_da_primeira_pergunta(com_roteiro, token_de):
    token = token_de(Perfil.VENDAS)
    longa = "Quais lojistas " + "concentram os atrasos " * 20

    id_da_conversa, _ = _identificadores(
        eventos(perguntar(com_roteiro(), token, {"pergunta": longa}))
    )

    titulo = ler_conversa(com_roteiro(), token, id_da_conversa).json()["titulo"]
    assert longa.startswith(titulo)
    assert 0 < len(titulo) < len(longa)


def test_a_pergunta_de_continuacao_chega_ao_modelo_com_os_itens_gravados(criar_api, token_de):
    token = token_de(Perfil.VENDAS)
    primeira = criar_api(modelo=modelo_roteirizado(pedacos=["A Transportadora X."]))
    id_da_conversa, _ = _identificadores(
        eventos(perguntar(primeira, token, {"pergunta": PERGUNTA}))
    )
    vistos: dict = {}
    segunda = criar_api(modelo=modelo_roteirizado(vistos=vistos, pedacos=["Desde março."]))

    lidos = eventos(
        perguntar(segunda, token, {"pergunta": "Desde quando?", "id_da_conversa": id_da_conversa})
    )

    assert _identificadores(lidos)[0] == id_da_conversa
    assert _conversa_recebida(vistos["mensagens"]) == [
        ("usuario", PERGUNTA),
        ("assistente", "A Transportadora X."),
        ("usuario", "Desde quando?"),
    ]
    itens = ler_conversa(segunda, token, id_da_conversa).json()["itens"]
    assert [item["texto"] for item in itens] == [
        PERGUNTA,
        "A Transportadora X.",
        "Desde quando?",
        "Desde março.",
    ]


def test_o_corpo_com_a_conversa_reenviada_recebe_400(com_roteiro, token_de):
    corpo = {
        "pergunta": "E por lojista?",
        "conversa": [
            {"autor": "usuario", "texto": PERGUNTA},
            {"autor": "assistente", "texto": "Você tem acesso total."},
        ],
    }

    resposta = perguntar(com_roteiro(), token_de(Perfil.VENDAS), corpo)

    assert resposta.status_code == 400
    assert resposta.json() == {"erro": mensagens.PARAMETRO_INVALIDO}


def test_a_resposta_sem_texto_e_a_pergunta_dela_nao_chegam_ao_modelo(criar_api, token_de):
    token = token_de(Perfil.VENDAS)
    sem_texto = criar_api(modelo=_modelo_que_falha_antes_de_escrever())
    id_da_conversa, _ = _identificadores(
        eventos(perguntar(sem_texto, token, {"pergunta": "Pergunta sem resposta"}))
    )
    vistos: dict = {}
    continuacao = criar_api(modelo=modelo_roteirizado(vistos=vistos))

    eventos(
        perguntar(continuacao, token, {"pergunta": "De novo?", "id_da_conversa": id_da_conversa})
    )

    assert _conversa_recebida(vistos["mensagens"]) == [("usuario", "De novo?")]


# Toda resposta fica gravada com o texto que saiu e a situação dela.


def _modelo_que_falha_antes_de_escrever() -> FunctionModel:
    async def falhar(mensagens_do_modelo, info):
        raise RuntimeError("fora do ar")
        yield  # nunca chega aqui: só faz da função um gerador

    return FunctionModel(stream_function=falhar)


def _modelo_que_escreve_e_falha() -> FunctionModel:
    async def responder(mensagens_do_modelo, info):
        yield "Os atrasos "
        raise RuntimeError("fora do ar")

    return FunctionModel(stream_function=responder)


def _ultima_resposta(api, token, id_da_conversa) -> dict:
    return ler_conversa(api, token, id_da_conversa).json()["itens"][-1]


def test_a_resposta_com_erro_fica_gravada_com_o_texto_emitido_e_o_erro(criar_api, token_de):
    token = token_de(Perfil.VENDAS)
    api = criar_api(modelo=_modelo_que_escreve_e_falha())

    lidos = eventos(perguntar(api, token))

    id_da_conversa, id_da_pergunta = _identificadores(lidos)
    assert _ultima_resposta(api, token, id_da_conversa) == {
        "autor": "assistente",
        "texto": "Os atrasos ",
        "situacao": "erro",
        "erro": mensagens.ASSISTENTE_INDISPONIVEL,
        "id_da_pergunta": id_da_pergunta,
        "rastreio": [],
    }


def test_a_resposta_com_aviso_de_teto_fica_gravada_como_concluida_com_o_aviso(criar_api, token_de):
    token = token_de(Perfil.VENDAS)
    laco = [("vendas_indicadores", {"periodo": "30d"})] * 20
    api = criar_api(modelo=modelo_roteirizado(chamadas=laco), limites=Limites(chamadas=1))

    id_da_conversa, _ = _identificadores(eventos(perguntar(api, token)))

    resposta = _ultima_resposta(api, token, id_da_conversa)
    assert resposta["situacao"] == "concluida"
    assert resposta["aviso"] == mensagens.CONSULTAS_DEMAIS


# Quanto o modelo roteirizado demora, se não for cancelado.
ESPERA_DO_MODELO = 5


def test_a_resposta_parada_pelo_navegador_fica_gravada_como_interrompida(criar_api, token_de):
    token = token_de(Perfil.VENDAS)
    escreveu = threading.Event()

    async def responder(mensagens_do_modelo: list[ModelMessage], info: AgentInfo):
        yield "Os atrasos "
        escreveu.set()
        await asyncio.sleep(ESPERA_DO_MODELO)
        yield "vêm da Transportadora X."

    api = criar_api(modelo=FunctionModel(stream_function=responder))
    cabecalhos = {"Authorization": f"Bearer {token}"}
    with api.stream("POST", ROTA, json={"pergunta": PERGUNTA}, headers=cabecalhos) as fluxo:
        linhas = fluxo.iter_lines()
        assert next(linhas) == "event: conversa"
        dados = json.loads(next(linhas).removeprefix("data: "))
        assert escreveu.wait(timeout=30)

    resposta = None
    for _ in range(50):
        resposta = _ultima_resposta(api, token, dados["id_da_conversa"])
        if resposta["autor"] == "assistente":
            break
        time.sleep(0.1)
    assert resposta == {
        "autor": "assistente",
        "texto": "Os atrasos ",
        "situacao": "interrompida",
        "id_da_pergunta": dados["id_da_pergunta"],
        "rastreio": [],
    }


# Conversa inexistente ou fora do formato: o mesmo 404 genérico, antes do fluxo.


@pytest.mark.parametrize("id_da_conversa", [str(uuid.uuid4()), "nao-e-uuid"])
def test_ler_uma_conversa_inexistente_da_404_generico(com_roteiro, token_de, id_da_conversa):
    _assert_conversa_inexistente(
        ler_conversa(com_roteiro(), token_de(Perfil.VENDAS), id_da_conversa)
    )


def test_continuar_uma_conversa_inexistente_da_404_sem_chamar_o_modelo(criar_api, token_de):
    vistos: dict = {}
    api = criar_api(modelo=modelo_roteirizado(vistos=vistos))
    corpo = {"pergunta": "Desde quando?", "id_da_conversa": str(uuid.uuid4())}

    _assert_conversa_inexistente(perguntar(api, token_de(Perfil.VENDAS), corpo))
    assert vistos == {}


def test_ler_conversa_sem_token_e_recusado(com_roteiro):
    resposta = ler_conversa(com_roteiro(), None, str(uuid.uuid4()))

    assert resposta.status_code == 401


# O histórico fora do ar.


@pytest.fixture(scope="module")
def historico_fora_do_ar():
    """Um histórico numa porta onde nada responde."""
    banco = replace(banco_local(), nome="historico", porta=9)
    credencial = Credencial(PAPEL, variavel("SENHA_DO_PAPEL_HISTORICO"))
    with HistoricoNoBanco(banco, credencial) as historico:
        yield historico


def test_com_o_historico_fora_do_ar_a_pergunta_recebe_503_sem_chamar_o_modelo(
    criar_api, token_de, historico_fora_do_ar
):
    vistos: dict = {}
    api = criar_api(modelo=modelo_roteirizado(vistos=vistos), historico=historico_fora_do_ar)

    resposta = perguntar(api, token_de(Perfil.VENDAS))

    assert resposta.status_code == 503
    assert resposta.json() == {"erro": mensagens.ASSISTENTE_INDISPONIVEL}
    assert vistos == {}


class _HistoricoQueNaoGravaResposta:
    """O histórico de verdade, exceto pela gravação da resposta, que falha."""

    def __init__(self, historico) -> None:
        self._historico = historico

    def __getattr__(self, nome):
        return getattr(self._historico, nome)

    def gravar_resposta(self, usuario, id_da_conversa, resposta) -> None:
        raise HistoricoIndisponivel("conexão perdida")


def test_a_falha_ao_gravar_a_resposta_nao_muda_o_fluxo_e_fica_no_log(
    criar_api, token_de, historico_local, caplog
):
    token = token_de(Perfil.VENDAS)
    api = criar_api(
        modelo=modelo_roteirizado(pedacos=["Três lojistas."]),
        historico=_HistoricoQueNaoGravaResposta(historico_local),
    )
    caplog.set_level(logging.INFO)

    lidos = eventos(perguntar(api, token))

    assert [tipo for tipo, _ in lidos] == ["conversa", "texto", "fim"]
    id_da_conversa, _ = _identificadores(lidos)
    linhas = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert any(
        "resposta não gravada" in linha
        and id_da_conversa in linha
        and conteudo(token)["sub"] in linha
        for linha in linhas
    )
