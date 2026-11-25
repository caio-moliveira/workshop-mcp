"""Fixtures das costuras de teste: o banco carregado (entrega 1) e a API por HTTP (entrega 2).

Desde a entrega 3, a API também lê o banco, pelo mecanismo de consultas, com o papel de cada perfil.
"""

import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import replace

import psycopg
import pytest
import uvicorn
from apoio import (
    BANCO_DA_AUDITORIA,
    BANCO_DO_HISTORICO,
    banco_local,
    compose,
    conectar_como_dono,
    limite_que_nao_barra,
    variavel,
)
from cliente_mcp import CAMINHO as CAMINHO_DO_MCP
from cliente_mcp import MCP_DO_AMBIENTE
from fastapi.testclient import TestClient
from provedor import (
    DESTINATARIO_DA_API,
    DESTINATARIO_DO_MCP,
    USUARIOS_DE_DEMONSTRACAO,
    emissor,
    token_pelo_fluxo_de_codigo,
    url_das_chaves,
)
from pydantic_ai.models import Model
from starlette.applications import Starlette

from acesso import ChavesDoProvedor, ConfiguracaoDeAcesso, Perfil
from api import criar_aplicacao
from assistente import Limites
from auditoria import PAPEL as PAPEL_DA_AUDITORIA
from auditoria import Auditoria, AuditoriaNoBanco
from consultas import Credencial, ExecutorDeConsultas, credenciais_do_ambiente
from historico import PAPEL as PAPEL_DO_HISTORICO
from historico import Historico, HistoricoNoBanco
from servidor_mcp import LimiteDeFrequencia
from servidor_mcp import criar_aplicacao as criar_aplicacao_mcp

# O token de acesso vale 5 minutos; um token guardado é trocado bem antes de vencer.
VALIDADE_DO_TOKEN_GUARDADO_EM_SEGUNDOS = 3 * 60

# O limite de frequência que o serviço `mcp` do compose precisa ter para a suíte: ela faz
# centenas de chamadas com o mesmo usuário. O limite de verdade é testado dentro do processo.
LIMITE_MINIMO_DO_MCP_PARA_A_SUITE = 10_000


@pytest.fixture(scope="session", autouse=True)
def mcp_do_ambiente_sem_limite_baixo() -> None:
    """Para a suíte logo no começo se o `mcp` do compose estiver com o limite da demonstração.

    Sem isto, dezenas de testes do servidor MCP falhariam com "Muitas chamadas", sem pista da
    causa. Se o serviço não responde, quem avisa são os próprios testes.
    """
    saida = compose("exec", "-T", "mcp", "printenv", "LIMITE_DE_CHAMADAS_POR_USUARIO")
    if saida.returncode != 0 or not saida.stdout.strip().isdigit():
        return
    if int(saida.stdout.strip()) < LIMITE_MINIMO_DO_MCP_PARA_A_SUITE:
        pytest.exit(
            "o serviço mcp do compose está com o limite de frequência baixo "
            f"({saida.stdout.strip()} chamadas); suba-o com "
            "LIMITE_DE_CHAMADAS_POR_USUARIO=100000 docker compose up -d --wait mcp",
            returncode=2,
        )


@pytest.fixture
def conexao_dono() -> Iterator[psycopg.Connection]:
    """Conexão com o banco carregado usando o papel dono."""
    with conectar_como_dono() as conexao:
        yield conexao


@pytest.fixture(scope="session")
def executor_de_consultas() -> Iterator[ExecutorDeConsultas]:
    """O executor de consultas com as credenciais do ambiente, apontado para o banco local."""
    with ExecutorDeConsultas(banco_local(), credenciais_do_ambiente()) as executor:
        yield executor


@pytest.fixture(scope="session")
def auditoria_local() -> Iterator[AuditoriaNoBanco]:
    """A auditoria do ambiente, com a credencial do papel `auditoria`, pela máquina local."""
    banco = replace(banco_local(), nome=BANCO_DA_AUDITORIA)
    credencial = Credencial(PAPEL_DA_AUDITORIA, variavel("SENHA_DO_PAPEL_AUDITORIA"))
    with AuditoriaNoBanco(banco, credencial) as registro:
        yield registro


@pytest.fixture(scope="session")
def historico_local() -> Iterator[HistoricoNoBanco]:
    """O histórico do ambiente, com a credencial do papel `historico`, pela máquina local."""
    banco = replace(banco_local(), nome=BANCO_DO_HISTORICO)
    credencial = Credencial(PAPEL_DO_HISTORICO, variavel("SENHA_DO_PAPEL_HISTORICO"))
    with HistoricoNoBanco(banco, credencial) as historico:
        yield historico


@pytest.fixture(scope="session")
def criar_api(executor_de_consultas, historico_local) -> Callable[..., TestClient]:
    """Cria a API pela fábrica, dentro do processo, validando tokens do provedor real.

    Cada parâmetro da configuração de acesso pode ser trocado: o relógio, as chaves, o emissor.
    O executor de consultas também, com `consultas=`, e o modelo de linguagem do assistente, com
    `modelo=` (sem ele, a API fica sem modelo, como sem a chave do provedor), e o servidor MCP
    que o assistente chama, com `endereco_do_mcp=` (sem ele, o serviço `mcp` do compose), e os
    tetos da pergunta, com `limites=` (sem ele, os padrões), e o histórico das conversas, com
    `historico=` (sem ele, o banco `historico` do compose). A origem do frontend liberada pelo
    CORS é a do ambiente.
    """

    def criar(
        consultas: ExecutorDeConsultas | None = None,
        modelo: Model | None = None,
        endereco_do_mcp: str = MCP_DO_AMBIENTE + CAMINHO_DO_MCP,
        limites: Limites | None = None,
        historico: Historico | None = None,
        **sobreposicoes,
    ) -> TestClient:
        configuracao = ConfiguracaoDeAcesso(
            emissor=emissor(),
            destinatario=DESTINATARIO_DA_API,
            chaves=ChavesDoProvedor(url_das_chaves()),
        )
        aplicacao = criar_aplicacao(
            replace(configuracao, **sobreposicoes),
            origem_do_frontend=variavel("ENDERECO_DO_FRONTEND"),
            consultas=consultas or executor_de_consultas,
            modelo=modelo,
            endereco_do_mcp=endereco_do_mcp,
            limites=limites or Limites(),
            historico=historico or historico_local,
        )
        return TestClient(aplicacao)

    return criar


@pytest.fixture(scope="session")
def criar_mcp(executor_de_consultas, auditoria_local) -> Callable[..., Starlette]:
    """Cria a aplicação do servidor MCP pela fábrica, dentro do processo.

    Como em `criar_api`: cada parâmetro da configuração de acesso pode ser trocado, e o executor
    de consultas também, com `consultas=`, a auditoria, com `auditoria=`, e o limite de
    frequência, com `limite=` (sem ele, um limite que nenhum teste alcança). O destinatário
    exigido é o do servidor MCP, e o endereço público anunciado nos metadados de recurso
    protegido é o do ambiente.
    """

    def criar(
        consultas: ExecutorDeConsultas | None = None,
        auditoria: Auditoria | None = None,
        limite: LimiteDeFrequencia | None = None,
        **sobreposicoes,
    ) -> Starlette:
        configuracao = ConfiguracaoDeAcesso(
            emissor=emissor(),
            destinatario=DESTINATARIO_DO_MCP,
            chaves=ChavesDoProvedor(url_das_chaves()),
        )
        return criar_aplicacao_mcp(
            replace(configuracao, **sobreposicoes),
            consultas or executor_de_consultas,
            auditoria or auditoria_local,
            endereco_publico=variavel("ENDERECO_PUBLICO_DO_MCP"),
            limite=limite or limite_que_nao_barra(),
        )

    return criar


@pytest.fixture(scope="module")
def mcp_no_processo(criar_mcp) -> Iterator[str]:
    """O endereço do servidor MCP criado pela fábrica, servido num uvicorn numa thread deste
    processo, numa porta livre: a API o chama pela rede, como chama o serviço `mcp` do compose,
    mas com as ferramentas deste código."""
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


@pytest.fixture
def api(criar_api) -> TestClient:
    """A API com a configuração de produção, apontada para o provedor real."""
    return criar_api()


@pytest.fixture(scope="module")
def token_de() -> Callable[[Perfil], str]:
    """O token de acesso do usuário de demonstração de um perfil, pelo fluxo de código.

    Guardado entre os testes de um módulo para não refazer o login a cada pedido, e trocado antes
    de vencer. Não passa de um módulo a outro: test_provedor_sem_estado reinicia o provedor, que
    volta com chaves novas e passa a recusar os tokens assinados antes.
    """
    guardados: dict[Perfil, tuple[str, float]] = {}

    def token(perfil: Perfil) -> str:
        guardado = guardados.get(perfil)
        if guardado and time.monotonic() - guardado[1] < VALIDADE_DO_TOKEN_GUARDADO_EM_SEGUNDOS:
            return guardado[0]
        demonstracao = next(u for u in USUARIOS_DE_DEMONSTRACAO if u.perfil == perfil)
        novo = token_pelo_fluxo_de_codigo(demonstracao.nome_de_usuario, demonstracao.senha())
        guardados[perfil] = (novo, time.monotonic())
        return novo

    return token
