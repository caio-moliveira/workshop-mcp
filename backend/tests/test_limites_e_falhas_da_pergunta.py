"""Os tetos da pergunta ao assistente e as falhas no meio da resposta.

Como na rota do assistente: a API é criada dentro do processo, com um modelo roteirizado, os
tetos montados pela fábrica, o token do provedor do compose e o serviço `mcp` do compose.
"""

import asyncio

import pytest
from provedor import OUTRA_APLICACAO, token_pelo_fluxo_de_codigo, usuario_de
from pydantic_ai.models.function import FunctionModel
from recusa import RESPOSTA_DE_PARAMETRO_INVALIDO
from roteiro import ASSISTENTE_INDISPONIVEL, eventos, modelo_roteirizado, perguntar

from acesso import Perfil
from assistente import Limites, limites_do_ambiente

# As mensagens genéricas do evento `erro`, ao lado da de assistente indisponível.
TEMPO_ESGOTADO = "O assistente demorou demais para responder. Tente de novo."
SESSAO_EXPIRADA = "Sua sessão expirou. Entre de novo para continuar."
# O que nenhuma mensagem ao usuário pode citar: provedor, modelo, ferramenta, protocolo e o
# detalhe da exceção (RS-08).
NOMES_INTERNOS = ["anthropic", "claude", "haiku", "vendas_indicadores", "mcp", "529", "overloaded"]

UM_LACO = [("vendas_indicadores", {"periodo": "30d"})] * 20


def _modelo_que_escreve_e_depois(acao) -> FunctionModel:
    """Escreve um trecho e então faz a `acao` (esperar, falhar) no meio da resposta."""

    async def responder(mensagens, info):
        yield "Os atrasos "
        await acao()
        yield "vêm da Transportadora X."

    return FunctionModel(stream_function=responder)


def _assert_um_unico_desfecho_generico(lidos) -> None:
    """O fluxo termina com exatamente um `fim` ou `erro`, sem nomes internos no desfecho."""
    tipos = [tipo for tipo, _ in lidos]
    assert tipos[-1] in ("fim", "erro")
    assert tipos.count("fim") + tipos.count("erro") == 1
    desfecho = str(lidos[-1][1]).lower()
    assert not [nome for nome in NOMES_INTERNOS if nome in desfecho]


def _fala(texto: str, autor: str = "usuario") -> dict:
    return {"autor": autor, "texto": texto}


# O teto de chamadas: a resposta para com um aviso, sem erro.


def test_o_modelo_em_laco_para_no_teto_de_chamadas_e_termina_com_fim_e_aviso(criar_api, token_de):
    api = criar_api(modelo=modelo_roteirizado(chamadas=UM_LACO), limites=Limites(chamadas=2))

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS)))

    tipo, dados = lidos[-1]
    assert tipo == "fim"
    assert dados["aviso"]
    assert [tipo for tipo, _ in lidos].count("estado") <= 3
    _assert_um_unico_desfecho_generico(lidos)


# Os tetos de tamanho: 400 antes de a resposta começar.


@pytest.mark.parametrize(
    "corpo",
    [
        {"pergunta": "x" * 51},
        {"pergunta": "Oi?", "conversa": [_fala("Oi")] * 21},
        {"pergunta": "Oi?", "conversa": [_fala("Oi"), _fala("x" * 51, "assistente")]},
    ],
    ids=["pergunta-grande-demais", "conversa-com-itens-demais", "item-da-conversa-grande-demais"],
)
def test_pedido_acima_dos_tetos_recebe_400_antes_da_resposta(criar_api, token_de, corpo):
    api = criar_api(modelo=modelo_roteirizado(), limites=Limites(caracteres=50))

    resposta = perguntar(api, token_de(Perfil.VENDAS), corpo)

    assert resposta.status_code == 400
    assert resposta.json() == RESPOSTA_DE_PARAMETRO_INVALIDO


def test_pedido_no_limite_dos_tetos_e_aceito(criar_api, token_de):
    api = criar_api(modelo=modelo_roteirizado(), limites=Limites(caracteres=50))
    corpo = {"pergunta": "x" * 50, "conversa": [_fala("x" * 50)] * 20}

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS), corpo))

    assert lidos[-1][0] == "fim"


# Falhas no meio da resposta: o texto que já saiu fica, e o fluxo termina com um `erro` genérico.


def test_modelo_lento_termina_com_erro_de_tempo_esgotado_sem_desfazer_o_texto(criar_api, token_de):
    async def demorar():
        await asyncio.sleep(5)

    api = criar_api(modelo=_modelo_que_escreve_e_depois(demorar), limites=Limites(segundos=0.5))

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS)))

    assert lidos == [("texto", {"texto": "Os atrasos "}), ("erro", {"erro": TEMPO_ESGOTADO})]
    _assert_um_unico_desfecho_generico(lidos)


def test_modelo_que_falha_no_meio_termina_com_erro_generico_sem_desfazer_o_texto(
    criar_api, token_de
):
    async def falhar():
        raise RuntimeError("anthropic claude-haiku-5-5 vendas_indicadores mcp: 529 overloaded")

    api = criar_api(modelo=_modelo_que_escreve_e_depois(falhar))

    lidos = eventos(perguntar(api, token_de(Perfil.VENDAS)))

    assert lidos == [
        ("texto", {"texto": "Os atrasos "}),
        ("erro", {"erro": ASSISTENTE_INDISPONIVEL}),
    ]
    _assert_um_unico_desfecho_generico(lidos)


def test_token_que_o_servidor_mcp_recusa_termina_com_erro_de_sessao_expirada(criar_api):
    # A API aceita o token da outra aplicação, que não traz o servidor MCP entre os
    # destinatários: o servidor MCP o recusa com 401, como um token vencido no meio da conversa.
    vendas = usuario_de(Perfil.VENDAS)
    token = token_pelo_fluxo_de_codigo(vendas.nome_de_usuario, vendas.senha(), OUTRA_APLICACAO)
    api = criar_api(
        modelo=modelo_roteirizado(chamadas=[("vendas_indicadores", {"periodo": "30d"})]),
        destinatario=OUTRA_APLICACAO,
    )

    lidos = eventos(perguntar(api, token))

    assert lidos == [("erro", {"erro": SESSAO_EXPIRADA})]
    _assert_um_unico_desfecho_generico(lidos)


# Os tetos vêm do ambiente, com padrão.


def test_sem_variaveis_de_ambiente_os_tetos_sao_os_padroes(monkeypatch):
    for nome in (
        "LIMITE_DE_CHAMADAS_POR_PERGUNTA",
        "LIMITE_DE_CARACTERES_DA_PERGUNTA",
        "TEMPO_MAXIMO_DA_PERGUNTA_EM_SEGUNDOS",
    ):
        monkeypatch.delenv(nome, raising=False)

    limites = limites_do_ambiente()

    assert (limites.chamadas, limites.caracteres, limites.segundos) == (8, 2000, 60)


def test_as_variaveis_de_ambiente_trocam_os_tetos(monkeypatch):
    monkeypatch.setenv("LIMITE_DE_CHAMADAS_POR_PERGUNTA", "3")
    monkeypatch.setenv("LIMITE_DE_CARACTERES_DA_PERGUNTA", "500")
    monkeypatch.setenv("TEMPO_MAXIMO_DA_PERGUNTA_EM_SEGUNDOS", "15")

    limites = limites_do_ambiente()

    assert (limites.chamadas, limites.caracteres, limites.segundos) == (3, 500, 15)
