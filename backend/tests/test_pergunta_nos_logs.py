"""A pergunta acompanhada nos logs, da API ao servidor MCP e às consultas, por um identificador
(RNF-06).

A API e o servidor MCP são criados dentro do processo, para o log dos dois cair no mesmo `caplog`.
O servidor MCP roda num uvicorn numa thread, numa porta livre: a API o chama pela rede, como
chama o serviço `mcp` do compose. O token é o do provedor do compose, e o banco, o carregado.
"""

import asyncio
import logging
import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn
from cliente_mcp import CAMINHO
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from provedor import conteudo
from recusa import pedir
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil
from consultas.pergunta_no_log import CABECALHO

PERGUNTA = "Pergunta que não pode ir para o log"
FERRAMENTA = "vendas_indicadores"
# O nome da consulta que a ferramenta serve, como aparece na linha do executor.
CONSULTA = "indicadores"


@pytest.fixture(scope="module")
def mcp_no_processo(criar_mcp) -> Iterator[str]:
    """O endereço do servidor MCP criado pela fábrica, servido numa thread deste processo."""
    # Sem `log_config`, o uvicorn não reconfigura o log do processo e o `caplog` continua valendo.
    configuracao = uvicorn.Config(
        criar_mcp(), host="127.0.0.1", port=0, log_config=None, log_level="warning"
    )
    servidor = uvicorn.Server(configuracao)
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


def _linhas(caplog, origem: str) -> list[str]:
    """As mensagens do log vindas do logger dado (ou de um filho dele)."""
    return [
        registro.getMessage()
        for registro in caplog.records
        if registro.name == origem or registro.name.startswith(origem + ".")
    ]


def test_o_mesmo_identificador_liga_a_pergunta_a_chamada_e_a_consulta(
    criar_api, mcp_no_processo, token_de, caplog
):
    caplog.set_level(logging.INFO)
    token = token_de(Perfil.VENDAS)
    api = criar_api(
        modelo=modelo_roteirizado(chamadas=[(FERRAMENTA, {"periodo": "30d"})]),
        endereco_do_mcp=mcp_no_processo + CAMINHO,
    )

    lidos = eventos(perguntar(api, token, {"pergunta": PERGUNTA}))

    _, inicio = lidos[0]
    pergunta, conversa = inicio["id_da_pergunta"], inicio["id_da_conversa"]
    usuario = conteudo(token)["sub"]
    da_pergunta = [linha for linha in _linhas(caplog, "assistente") if pergunta in linha]
    assert any("iniciada" in linha for linha in da_pergunta)
    assert any("terminada" in linha for linha in da_pergunta)
    assert all(conversa in linha and usuario in linha for linha in da_pergunta)
    da_chamada = [linha for linha in _linhas(caplog, "servidor_mcp") if pergunta in linha]
    assert any(FERRAMENTA in linha and "permitida" in linha for linha in da_chamada)
    da_consulta = [linha for linha in _linhas(caplog, "consultas") if pergunta in linha]
    assert any(CONSULTA in linha and " ms" in linha for linha in da_consulta)
    assert not any(PERGUNTA in registro.getMessage() for registro in caplog.records)


def test_a_consulta_de_uma_rota_das_telas_tambem_tem_linha_sem_identificador(api, token_de, caplog):
    caplog.set_level(logging.INFO)

    resposta = pedir(api, "/vendas/indicadores", token_de(Perfil.VENDAS), periodo="30d")

    assert resposta.status_code == 200
    assert any(
        CONSULTA in linha and " ms" in linha and "sem pergunta" in linha
        for linha in _linhas(caplog, "consultas")
    )


def _chamar_com_cabecalhos(endereco: str, token: str, cabecalhos: dict[str, str]):
    async def chamar():
        transporte = StreamableHttpTransport(endereco + CAMINHO, auth=token, headers=cabecalhos)
        async with Client(transporte) as cliente:
            return await cliente.call_tool(FERRAMENTA, {"periodo": "30d"}, raise_on_error=False)

    return asyncio.run(chamar())


@pytest.mark.parametrize(
    "cabecalhos",
    [
        {},
        {CABECALHO: "nao-e-uuid; linha forjada"},
        {CABECALHO: "{12345678-1234-1234-1234-1234567890ab}"},
    ],
    ids=["sem-cabecalho", "fora-do-formato", "uuid-com-chaves"],
)
def test_o_servidor_mcp_ignora_o_identificador_fora_do_formato_e_atende_sem_ele(
    mcp_no_processo, token_de, caplog, cabecalhos
):
    """Um assistente externo não manda o cabeçalho, e ninguém escreve o que quiser no log."""
    caplog.set_level(logging.INFO)

    resultado = _chamar_com_cabecalhos(mcp_no_processo, token_de(Perfil.VENDAS), cabecalhos)

    assert not resultado.is_error
    assert any(
        FERRAMENTA in linha and "permitida" in linha and "sem pergunta" in linha
        for linha in _linhas(caplog, "servidor_mcp")
    )
    for valor in cabecalhos.values():
        assert not any(valor in registro.getMessage() for registro in caplog.records)
