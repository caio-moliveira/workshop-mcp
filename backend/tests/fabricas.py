"""A API criada pela fábrica, dentro do processo, validando tokens do provedor real.

Usada pela fixture `criar_api` do `conftest.py` e pela execução de aceite, que cria a API com o
modelo roteirizado do cenário do assistente.
"""

from dataclasses import replace
from pathlib import Path

from apoio import variavel
from cliente_mcp import CAMINHO as CAMINHO_DO_MCP
from cliente_mcp import MCP_DO_AMBIENTE
from fastapi.testclient import TestClient
from provedor import DESTINATARIO_DA_API, emissor, url_das_chaves
from pydantic_ai.models import Model

from acesso import ChavesDoProvedor, ConfiguracaoDeAcesso
from api import criar_aplicacao
from assistente import Limites
from auditoria import LeituraDaAuditoria
from consultas import ExecutorDeConsultas
from historico import Historico


def api_no_processo(
    consultas: ExecutorDeConsultas,
    historico: Historico,
    modelo: Model | None = None,
    endereco_do_mcp: str = MCP_DO_AMBIENTE + CAMINHO_DO_MCP,
    limites: Limites | None = None,
    execucao_de_aceite: Path | None = None,
    leitura_da_auditoria: LeituraDaAuditoria | None = None,
    **sobreposicoes,
) -> TestClient:
    """A API com a configuração de acesso do provedor real, em que cada parâmetro pode ser
    trocado (`sobreposicoes`), e o assistente apontado para o servidor MCP em `endereco_do_mcp`.
    A origem do frontend liberada pelo CORS é a do ambiente."""
    configuracao = ConfiguracaoDeAcesso(
        emissor=emissor(),
        destinatario=DESTINATARIO_DA_API,
        chaves=ChavesDoProvedor(url_das_chaves()),
    )
    aplicacao = criar_aplicacao(
        replace(configuracao, **sobreposicoes),
        origem_do_frontend=variavel("ENDERECO_DO_FRONTEND"),
        consultas=consultas,
        modelo=modelo,
        endereco_do_mcp=endereco_do_mcp,
        limites=limites or Limites(),
        historico=historico,
        execucao_de_aceite=execucao_de_aceite,
        leitura_da_auditoria=leitura_da_auditoria,
    )
    return TestClient(aplicacao)
