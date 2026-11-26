"""A execução de aceite: todos os cenários de segurança contra o ambiente no ar (entrega 11).

Dentro de `backend/`, com o ambiente no ar:

    uv run python tests/execucao_de_aceite.py

Mostra o andamento e o resumo no terminal e grava o resultado em `backend/execucao-de-aceite/`,
no lugar do anterior; a API o lê de lá para o painel de segurança. Termina com código 1 se algum
cenário divergiu do esperado.

Não é o pytest: é um comando próprio, que usa os mesmos auxiliares dos testes (o token pelo fluxo
de código com PKCE, o pedido à API). O esperado de cada cenário de rota vem do registro de donos
das rotas, nunca é escrito à mão: um cenário com resultado diferente do esperado é gravado como
divergência, e não escondido.

Os cenários ficam agrupados pela camada de defesa: cada grupo tem a sua função em
`CENARIOS_POR_GRUPO`, e um grupo novo é só uma função a mais ali.
"""

import argparse
import asyncio
import os
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402
import psycopg  # noqa: E402
from apoio import (  # noqa: E402
    BANCO_DA_AUDITORIA,
    banco_local,
    conectar_como_dono,
    conectar_como_perfil,
    variavel,
)
from cliente_mcp import CAMINHO, FERRAMENTA_DESCONHECIDA, MCP_DO_AMBIENTE, chamar  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.client.client import CallToolResult  # noqa: E402
from fastmcp.client.transports import StreamableHttpTransport  # noqa: E402
from provedor import (  # noqa: E402
    DESTINATARIO_DA_API,
    USUARIOS_DE_DEMONSTRACAO,
    conteudo,
    emissor,
    token_pelo_fluxo_de_codigo,
    url_das_chaves,
    usuario_de,
)
from pydantic_ai.messages import ModelRequest, ToolReturnPart  # noqa: E402
from registros import DONO_DA_FERRAMENTA, DONO_DA_ROTA, argumentos_minimos  # noqa: E402
from roteiro import eventos, modelo_roteirizado, perguntar  # noqa: E402
from starlette.applications import Starlette  # noqa: E402

from aceite import (  # noqa: E402
    GRUPOS,
    Alvo,
    CamadaDeDefesa,
    Cenario,
    ConferenciaDaCarga,  # noqa: E402
    Desfecho,
    ExecucaoDeAceite,
    Grupo,
    LinhaDaAuditoria,
    MatrizCompleta,
    Quem,
    Resposta,
    gravar_execucao,
)
from acesso import ChavesDoProvedor, ConfiguracaoDeAcesso, Perfil, UsuarioAutenticado, mensagens  # noqa: E402
from api import criar_aplicacao as criar_api  # noqa: E402
from carga.configuracao import ler_configuracao  # noqa: E402
from consultas import (  # noqa: E402
    Credencial,  # noqa: E402
    ExecutorDeConsultas,
    credenciais_do_ambiente,
)
from historico import BANCO as BANCO_DO_HISTORICO  # noqa: E402
from historico import PAPEL as PAPEL_DO_HISTORICO  # noqa: E402
from historico import HistoricoNoBanco  # noqa: E402
from servidor_mcp.limite import CHAMADAS_PADRAO  # noqa: E402

API = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"
PASTA_PADRAO = Path(__file__).resolve().parents[1] / "execucao-de-aceite"

# O token de acesso vale 5 minutos; um token guardado é trocado bem antes de vencer.
VALIDADE_DO_TOKEN_GUARDADO_EM_SEGUNDOS = 3 * 60

NEGACAO_DA_ROTA = (403, mensagens.ACESSO_NEGADO)
CONVERSA_INEXISTENTE = (404, mensagens.CONVERSA_INEXISTENTE)


@dataclass(frozen=True)
class Observado:
    """O que um cenário obteve. `confere` diz se a resposta tem a forma esperada além do
    desfecho: uma negação com outro status ou outra mensagem também é divergência."""

    obtido: Desfecho
    resposta: Resposta
    auditoria: LinhaDaAuditoria | None = None
    confere: bool = True


@dataclass(frozen=True)
class CenarioDeSeguranca:
    """Um cenário de segurança a executar: quem pede o quê, o esperado e como executá-lo."""

    id: str
    descricao: str
    grupo: Grupo
    quem: Quem
    perfil: Perfil | None
    alvo: Alvo
    camadas_de_defesa: tuple[CamadaDeDefesa, ...]
    esperado: Desfecho
    executar: Callable[["Contexto"], Observado] = field(compare=False, repr=False)
    # O que o cenário precisa antes do pedido (o login, a conversa de outro usuário), fora da
    # duração medida: a duração é a do pedido.
    preparar: Callable[["Contexto"], object] = field(
        default=lambda _: None, compare=False, repr=False
    )
    # O cenário do limite de frequência exige o servidor MCP no limite padrão: fica fora do
    # teste contra o compose, que roda com o limite alto da suíte.
    exige_limite_padrao: bool = False


class Contexto:
    """O que os cenários de uma execução compartilham: o cliente da API, os tokens já obtidos e
    o que for preciso preparar (a conversa de outro usuário). Feche ao terminar."""

    def __init__(self, endereco_da_api: str = API) -> None:
        self.api = httpx.Client(base_url=endereco_da_api, timeout=30)
        self._tokens: dict[str, tuple[str, float]] = {}
        self._historico: HistoricoNoBanco | None = None
        self._conversas: dict[str, tuple[UsuarioAutenticado, uuid.UUID]] = {}

    def token_de(self, nome_de_usuario: str) -> str:
        """O token de acesso do usuário de demonstração, pelo fluxo de código, guardado."""
        guardado = self._tokens.get(nome_de_usuario)
        if guardado and time.monotonic() - guardado[1] < VALIDADE_DO_TOKEN_GUARDADO_EM_SEGUNDOS:
            return guardado[0]
        token = token_pelo_fluxo_de_codigo(nome_de_usuario, _usuario(nome_de_usuario).senha())
        self._tokens[nome_de_usuario] = (token, time.monotonic())
        return token

    def conversa_de(self, nome_de_usuario: str) -> uuid.UUID:
        """Uma conversa do usuário, criada no histórico para a execução e apagada no fim."""
        if nome_de_usuario not in self._conversas:
            demonstracao = _usuario(nome_de_usuario)
            dono = UsuarioAutenticado(
                id=conteudo(self.token_de(nome_de_usuario))["sub"],
                nome=demonstracao.nome,
                perfil=demonstracao.perfil,
            )
            identificador = self._historico_do_ambiente().criar_conversa(
                dono, "Conversa da execução de aceite", uuid.uuid4()
            )
            self._conversas[nome_de_usuario] = (dono, identificador)
        return self._conversas[nome_de_usuario][1]

    def _historico_do_ambiente(self) -> HistoricoNoBanco:
        if self._historico is None:
            banco = replace(banco_local(), nome=BANCO_DO_HISTORICO)
            credencial = Credencial(PAPEL_DO_HISTORICO, variavel("SENHA_DO_PAPEL_HISTORICO"))
            self._historico = HistoricoNoBanco(banco, credencial)
        return self._historico

    def fechar(self) -> None:
        for dono, identificador in self._conversas.values():
            self._historico_do_ambiente().apagar_conversa(dono, identificador)
        if self._historico is not None:
            self._historico.fechar()
        self.api.close()

    def __enter__(self) -> "Contexto":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()


def _usuario(nome_de_usuario: str):
    return next(u for u in USUARIOS_DE_DEMONSTRACAO if u.nome_de_usuario == nome_de_usuario)


def _linhas(corpo) -> int:
    """A quantidade de linhas de uma resposta permitida, e nada do conteúdo: o tamanho da maior
    lista do corpo, ou 1 para um corpo sem lista (um cartão de indicadores)."""
    if isinstance(corpo, list):
        return len(corpo)
    if isinstance(corpo, dict):
        listas = [len(valor) for valor in corpo.values() if isinstance(valor, list)]
        return max(listas, default=1)
    return 1


def _observar_resposta(resposta: httpx.Response, negacao_esperada: tuple[int, str]) -> Observado:
    """O desfecho de um pedido à API: 2xx é permitido, com o status e as linhas; o resto é
    negado, com o status e a mensagem, e confere só se for a negação esperada."""
    if resposta.is_success:
        return Observado(
            "permitido", Resposta(status=resposta.status_code, linhas=_linhas(resposta.json()))
        )
    try:
        mensagem = resposta.json().get("erro")
    except ValueError:
        mensagem = None
    observado = Resposta(status=resposta.status_code, mensagem=mensagem)
    return Observado(
        "negado", observado, confere=(resposta.status_code, mensagem) == negacao_esperada
    )


# --- Camada de defesa API ---


def _esperado_da_rota(rota: str, perfil: Perfil) -> Desfecho:
    """Só o dono da rota, pelo registro, lê a rota."""
    return "permitido" if DONO_DA_ROTA[rota] is perfil else "negado"


def leitura_de_rota(
    id: str,
    descricao: str,
    nome_de_usuario: str,
    rota: str,
    parametros: dict[str, str] | None = None,
) -> CenarioDeSeguranca:
    """Um usuário lê uma rota de dados da API; o esperado vem do registro de donos."""
    perfil = _usuario(nome_de_usuario).perfil
    parametros = parametros or {}

    def executar(contexto: Contexto) -> Observado:
        token = contexto.token_de(nome_de_usuario)
        resposta = contexto.api.get(
            rota, headers={"Authorization": f"Bearer {token}"}, params=parametros
        )
        return _observar_resposta(resposta, NEGACAO_DA_ROTA)

    return CenarioDeSeguranca(
        id=id,
        descricao=descricao,
        grupo="api",
        quem=Quem(tipo="usuario", nome=nome_de_usuario),
        perfil=perfil,
        alvo=Alvo(tipo="rota", nome=rota, parametros=parametros),
        camadas_de_defesa=("api",),
        esperado=_esperado_da_rota(rota, perfil),
        executar=executar,
        preparar=lambda contexto: contexto.token_de(nome_de_usuario),
    )


def leitura_da_conversa_de_outro(
    id: str, descricao: str, nome_de_usuario: str, dono_da_conversa: str
) -> CenarioDeSeguranca:
    """Um usuário lê a conversa de outro: responde como uma conversa que não existe (RF-18)."""

    def executar(contexto: Contexto) -> Observado:
        identificador = contexto.conversa_de(dono_da_conversa)
        token = contexto.token_de(nome_de_usuario)
        resposta = contexto.api.get(
            f"/conversas/{identificador}", headers={"Authorization": f"Bearer {token}"}
        )
        return _observar_resposta(resposta, CONVERSA_INEXISTENTE)

    return CenarioDeSeguranca(
        id=id,
        descricao=descricao,
        grupo="api",
        quem=Quem(tipo="usuario", nome=nome_de_usuario),
        perfil=_usuario(nome_de_usuario).perfil,
        alvo=Alvo(
            tipo="conversa",
            nome="/conversas/{id_da_conversa}",
            parametros={"dono": dono_da_conversa},
        ),
        camadas_de_defesa=("api",),
        # Só o dono alcança a própria conversa.
        esperado="permitido" if nome_de_usuario == dono_da_conversa else "negado",
        executar=executar,
        preparar=lambda contexto: (
            contexto.conversa_de(dono_da_conversa),
            contexto.token_de(nome_de_usuario),
        ),
    )


def cenarios_da_api() -> list[CenarioDeSeguranca]:
    return [
        leitura_de_rota(
            "api-dono-le-a-propria-rota",
            "O dono lê a própria rota",
            "ana.vendas",
            "/vendas/pedidos-recentes",
        ),
        leitura_de_rota(
            "api-vendas-le-rota-da-diretoria",
            "Vendas lê uma rota da Diretoria",
            "ana.vendas",
            "/diretoria/indicadores",
        ),
        leitura_de_rota(
            "api-produtos-le-rota-do-comercial",
            "Produtos lê uma rota do Comercial e recebe o mesmo 403",
            "bruno.produtos",
            "/comercial/indicadores",
        ),
        leitura_de_rota(
            "api-periodo-invalido-em-rota-alheia",
            "Um período inválido numa rota alheia é negado antes da validação",
            "ana.vendas",
            "/diretoria/resumo",
            {"periodo": "7d"},
        ),
        leitura_da_conversa_de_outro(
            "api-conversa-de-outro-usuario",
            "A conversa de outro usuário responde como inexistente",
            "ana.vendas",
            "vitor.vendas",
        ),
    ]


# --- A auditoria, lida pelo dono ---


def _ultimo_id_da_auditoria() -> int:
    """O identificador da linha mais recente da auditoria: o marco antes de um pedido."""
    with conectar_como_dono(BANCO_DA_AUDITORIA) as conexao:
        return conexao.execute("select coalesce(max(id), 0) from auditoria.chamada").fetchone()[0]


def _linhas_da_auditoria_desde(id_do_usuario: str, depois_do_id: int) -> list[LinhaDaAuditoria]:
    """As linhas que as chamadas do usuário (o `sub` do token) deixaram depois do marco."""
    with conectar_como_dono(BANCO_DA_AUDITORIA) as conexao:
        linhas = conexao.execute(
            "select id, horario, nome_do_usuario, ferramenta, parametros, resultado"
            " from auditoria.chamada where id_do_usuario = %s and id > %s order by id",
            (id_do_usuario, depois_do_id),
        ).fetchall()
    return [
        LinhaDaAuditoria(
            id=id,
            horario=horario,
            usuario=usuario,
            ferramenta=ferramenta,
            argumentos=argumentos,
            resultado=resultado,
        )
        for id, horario, usuario, ferramenta, argumentos, resultado in linhas
    ]


# --- Camada de defesa Banco ---

# O que o cenário mostra quando o banco recusa: o código do Postgres para privilégio insuficiente,
# sem o texto do erro.
RECUSA_DO_BANCO = "Recusado pelo banco: o papel não tem o privilégio (42501)."


def _esperado_no_banco(papel: Perfil, objeto: str, escrita: bool) -> Desfecho:
    """Cada papel lê só a própria camada de leitura e não escreve em nada (ADR 0002)."""
    esquema = objeto.split(".")[0]
    return "permitido" if not escrita and esquema == papel.value else "negado"


def acesso_ao_banco(
    id: str, descricao: str, papel: Perfil, objeto: str, escrita: str | None = None
) -> CenarioDeSeguranca:
    """Um papel do banco, com a própria credencial, lê o objeto ou, com `escrita`, executa esse
    comando nele. A escrita é inócua mesmo se passasse: não muda linha nenhuma e é desfeita."""

    def executar(_: Contexto) -> Observado:
        with conectar_como_perfil(papel) as conexao:
            try:
                if escrita:
                    # Só os privilégios podem barrar: a sessão pede transações de escrita.
                    conexao.execute("set default_transaction_read_only = off")
                    with conexao.transaction(force_rollback=True):
                        conexao.execute(escrita)
                    return Observado("permitido", Resposta(status=None, linhas=0))
                linhas = conexao.execute(f"select count(*) from {objeto}").fetchone()[0]
            except psycopg.errors.InsufficientPrivilege:
                return Observado("negado", Resposta(status=None, mensagem=RECUSA_DO_BANCO))
        return Observado("permitido", Resposta(status=None, linhas=linhas))

    origem = objeto.startswith("dados_de_origem.")
    return CenarioDeSeguranca(
        id=id,
        descricao=descricao,
        grupo="banco",
        quem=Quem(tipo="papel", nome=papel.value),
        perfil=papel,
        alvo=Alvo(
            tipo="dados_de_origem" if origem else "camada_de_leitura",
            nome=objeto,
            parametros={"comando": escrita} if escrita else {},
        ),
        camadas_de_defesa=("banco",),
        esperado=_esperado_no_banco(papel, objeto, escrita is not None),
        executar=executar,
    )


def cenarios_do_banco() -> list[CenarioDeSeguranca]:
    return [
        acesso_ao_banco(
            "banco-vendas-le-a-propria-camada",
            "O papel vendas lê a própria camada de leitura",
            Perfil.VENDAS,
            "vendas.pedido",
        ),
        acesso_ao_banco(
            "banco-vendas-le-a-camada-da-diretoria",
            "O papel vendas é recusado na camada da Diretoria",
            Perfil.VENDAS,
            "diretoria.indicadores",
        ),
        acesso_ao_banco(
            "banco-diretoria-le-os-dados-de-origem",
            "O papel diretoria é recusado nos dados de origem",
            Perfil.DIRETORIA,
            "dados_de_origem.pedido",
        ),
        acesso_ao_banco(
            "banco-comercial-escreve-na-propria-camada",
            "O papel comercial não escreve, nem na própria camada",
            Perfil.COMERCIAL,
            "comercial.lead",
            escrita="update comercial.lead set etapa = etapa where false",
        ),
    ]


# --- Camada de defesa Limite de frequência ---

FERRAMENTA_DO_LIMITE = "vendas_indicadores"
ARGUMENTOS_DO_LIMITE = {"periodo": "30d"}
# Uma chamada além do limite padrão: com ele, a última é barrada.
CHAMADAS_ALEM_DO_LIMITE = CHAMADAS_PADRAO + 1


def chamadas_seguidas(
    id: str,
    descricao: str,
    nome_de_usuario: str,
    chamadas: int,
    esperado: Desfecho,
    servidor: str | Starlette = MCP_DO_AMBIENTE,
) -> CenarioDeSeguranca:
    """O usuário chama a mesma ferramenta até `chamadas` vezes seguidas, parando na primeira
    barrada; o obtido é o da última. Exige o servidor MCP no limite padrão."""

    def executar(contexto: Contexto) -> Observado:
        token = contexto.token_de(nome_de_usuario)
        antes = _ultimo_id_da_auditoria()
        for _ in range(chamadas):
            resultado = chamar(servidor, token, FERRAMENTA_DO_LIMITE, ARGUMENTOS_DO_LIMITE)
            if resultado.is_error:
                break
        linhas = _linhas_da_auditoria_desde(conteudo(token)["sub"], antes)
        ultima = linhas[-1] if linhas else None
        if resultado.is_error:
            mensagem = resultado.content[0].text
            limitada = ultima is not None and ultima.resultado == "limitada"
            return Observado(
                "negado",
                Resposta(status=None, mensagem=mensagem),
                ultima,
                confere=limitada and mensagem == mensagens.MUITAS_CHAMADAS,
            )
        return Observado(
            "permitido",
            Resposta(status=None, linhas=_linhas(resultado.structured_content)),
            ultima,
            confere=ultima is not None and ultima.resultado == "permitida",
        )

    return CenarioDeSeguranca(
        id=id,
        descricao=descricao,
        grupo="limite_de_frequencia",
        quem=Quem(tipo="usuario", nome=nome_de_usuario),
        perfil=_usuario(nome_de_usuario).perfil,
        alvo=Alvo(
            tipo="ferramenta",
            nome=FERRAMENTA_DO_LIMITE,
            parametros={**ARGUMENTOS_DO_LIMITE, "chamadas": chamadas},
        ),
        camadas_de_defesa=("limite_de_frequencia",),
        esperado=esperado,
        executar=executar,
        preparar=lambda contexto: contexto.token_de(nome_de_usuario),
        exige_limite_padrao=True,
    )


def cenarios_do_limite(servidor: str | Starlette = MCP_DO_AMBIENTE) -> list[CenarioDeSeguranca]:
    """O Vitor passa do limite, e não a Ana: ela não fica barrada no meio da apresentação."""
    return [
        chamadas_seguidas(
            "limite-vitor-passa-do-limite",
            f"vitor.vendas faz {CHAMADAS_ALEM_DO_LIMITE} chamadas seguidas e é barrado",
            "vitor.vendas",
            CHAMADAS_ALEM_DO_LIMITE,
            "negado",
            servidor,
        ),
        chamadas_seguidas(
            "limite-ana-continua-passando",
            "ana.vendas, logo depois, continua passando: o limite é por usuário",
            "ana.vendas",
            1,
            "permitido",
            servidor,
        ),
    ]


# --- Assistente, com o modelo roteirizado ---

PERGUNTA_AO_ASSISTENTE = "Quanto vendemos no último mês?"
# O que o cenário mostra quando a ferramenta de outro perfil é recusada: o nome que o servidor não
# listou para o token é recusado dentro da API, sem chegar ao servidor.
RECUSA_NO_ASSISTENTE = "Recusada na chamada: a ferramenta não está na lista do token."


def _api_com_modelo(modelo, historico: HistoricoNoBanco, consultas: ExecutorDeConsultas):
    """A API criada pela fábrica, dentro do processo, com o modelo dado e o serviço `mcp` do
    compose: o assistente chama o servidor MCP com o token de quem pergunta."""
    configuracao = ConfiguracaoDeAcesso(
        emissor=emissor(),
        destinatario=DESTINATARIO_DA_API,
        chaves=ChavesDoProvedor(url_das_chaves()),
    )
    aplicacao = criar_api(
        configuracao,
        origem_do_frontend=variavel("ENDERECO_DO_FRONTEND"),
        consultas=consultas,
        modelo=modelo,
        endereco_do_mcp=MCP_DO_AMBIENTE + CAMINHO,
        historico=historico,
    )
    return TestClient(aplicacao)


def pergunta_ao_assistente(
    id: str, descricao: str, nome_de_usuario: str, ferramenta: str
) -> CenarioDeSeguranca:
    """O usuário pergunta ao assistente, e o modelo roteirizado chama a ferramenta dada. O esperado
    vem do registro de donos das ferramentas."""
    demonstracao = _usuario(nome_de_usuario)
    argumentos = {**argumentos_minimos(ferramenta), "periodo": "30d"}
    esperado: Desfecho = (
        "permitido" if DONO_DA_FERRAMENTA[ferramenta] is demonstracao.perfil else "negado"
    )

    def executar(contexto: Contexto) -> Observado:
        token = contexto.token_de(nome_de_usuario)
        do_token = conteudo(token)
        historico = contexto._historico_do_ambiente()
        vistos: dict = {}
        modelo = modelo_roteirizado(
            chamadas=[(ferramenta, argumentos)], pedacos=["Ok."], vistos=vistos
        )
        antes = _ultimo_id_da_auditoria()
        with ExecutorDeConsultas(banco_local(), credenciais_do_ambiente()) as consultas:
            api = _api_com_modelo(modelo, historico, consultas)
            resposta = perguntar(api, token, {"pergunta": PERGUNTA_AO_ASSISTENTE})
            lidos = eventos(resposta)
        # A conversa da pergunta é só da execução: sai do histórico.
        dono = UsuarioAutenticado(
            id=do_token["sub"], nome=demonstracao.nome, perfil=demonstracao.perfil
        )
        historico.apagar_conversa(dono, uuid.UUID(lidos[0][1]["id_da_conversa"]))

        linhas = _linhas_da_auditoria_desde(do_token["sub"], antes)
        retornos = [
            parte
            for mensagem in vistos["mensagens"]
            if isinstance(mensagem, ModelRequest)
            for parte in mensagem.parts
            if isinstance(parte, ToolReturnPart) and parte.outcome == "success"
        ]
        if retornos:
            [linha] = linhas or [None]
            return Observado(
                "permitido",
                Resposta(status=resposta.status_code, linhas=_linhas(retornos[0].content)),
                linha,
                confere=len(linhas) == 1
                and linha.usuario == do_token["name"]
                and linha.ferramenta == ferramenta
                and linha.resultado == "permitida",
            )
        # Negada antes do servidor: nenhuma linha nova na auditoria, muito menos uma permitida.
        return Observado(
            "negado",
            Resposta(status=resposta.status_code, mensagem=RECUSA_NO_ASSISTENTE),
            confere=not linhas,
        )

    return CenarioDeSeguranca(
        id=id,
        descricao=descricao,
        grupo="assistente",
        quem=Quem(tipo="usuario", nome=nome_de_usuario),
        perfil=demonstracao.perfil,
        alvo=Alvo(
            tipo="assistente",
            nome="/assistente",
            parametros={"ferramenta": ferramenta, **argumentos},
        ),
        # A ferramenta de outro perfil não está na lista do token, e a chamada a ela é recusada.
        camadas_de_defesa=("chamada",)
        if esperado == "permitido"
        else (
            "lista_de_ferramentas",
            "chamada",
        ),
        esperado=esperado,
        executar=executar,
        preparar=lambda contexto: contexto.token_de(nome_de_usuario),
    )


def cenarios_do_assistente() -> list[CenarioDeSeguranca]:
    return [
        pergunta_ao_assistente(
            "assistente-chama-o-mcp-com-o-token-do-usuario",
            "O assistente chama o servidor MCP com o token do usuário (RF-15)",
            "bruno.produtos",
            "produtos_indicadores",
        ),
        pergunta_ao_assistente(
            "assistente-ferramenta-de-outro-perfil",
            "O modelo tenta uma ferramenta de outro perfil e é negado na chamada",
            "bruno.produtos",
            "comercial_indicadores",
        ),
    ]


# Os cenários de cada grupo da matriz, na ordem em que um pedido atravessa as camadas de defesa.
# Um grupo ainda sem cenários fica de fora.
CENARIOS_POR_GRUPO: dict[Grupo, Callable[[], list[CenarioDeSeguranca]]] = {
    "api": cenarios_da_api,
}
CENARIOS_POR_GRUPO |= {
    "banco": cenarios_do_banco,
    "limite_de_frequencia": cenarios_do_limite,
    "assistente": cenarios_do_assistente,
}


# --- A conferência da carga ---

# O banco da carga padrão (configuração versionada da carga): as linhas de cada tabela dos dados
# de origem. A data de referência vem da própria configuração.
CONTAGENS_DE_REFERENCIA = {
    "avaliacao": 20114,
    "categoria": 20,
    "cliente": 28511,
    "entrega": 28789,
    "item_pedido": 41118,
    "lead": 1500,
    "lojista": 300,
    "pagamento": 29999,
    "pedido": 29999,
    "produto": 2000,
    "referencia": 1,
}


def conferir_carga(
    data_de_referencia: date | None = None,
    contagens: dict[str, int] = CONTAGENS_DE_REFERENCIA,
) -> ConferenciaDaCarga:
    """Se o banco está no estado da carga: a data de referência (por padrão, a da configuração
    da carga) e as contagens de referência, lidas com o papel dono."""
    esperada = data_de_referencia or ler_configuracao().data_referencia
    try:
        with conectar_como_dono() as conexao:
            data = conexao.execute(
                "select data_referencia from dados_de_origem.referencia"
            ).fetchone()[0]
            obtidas = {
                tabela: conexao.execute(
                    f"select count(*) from dados_de_origem.{tabela}"
                ).fetchone()[0]
                for tabela in contagens
            }
    except psycopg.Error as erro:
        return ConferenciaDaCarga(
            confere=False, detalhe=f"o banco não pôde ser lido ({type(erro).__name__})"
        )
    diferencas = []
    if data != esperada:
        diferencas.append(f"data de referência {data}, esperada {esperada}")
    diferencas += [
        f"{tabela} com {obtidas[tabela]} linhas, esperadas {esperado}"
        for tabela, esperado in contagens.items()
        if obtidas[tabela] != esperado
    ]
    return ConferenciaDaCarga(
        confere=not diferencas,
        data_de_referencia=data,
        detalhe="; ".join(diferencas) or None,
    )


def _linha_da_carga(carga: ConferenciaDaCarga) -> str:
    if carga.confere:
        return (
            f"Carga: o banco está no estado da carga (data de referência "
            f"{carga.data_de_referencia}, contagens de referência conferidas)."
        )
    return f"AVISO: o banco não está no estado da carga: {carga.detalhe}."


def cenarios() -> list[CenarioDeSeguranca]:
    """Todos os cenários de segurança, agrupados pela camada de defesa."""
    return [
        cenario
        for grupo in GRUPOS
        if grupo in CENARIOS_POR_GRUPO
        for cenario in CENARIOS_POR_GRUPO[grupo]()
    ]


# --- A matriz completa ---


@dataclass(frozen=True)
class ParDaMatriz:
    """Um par da matriz completa: uma rota ou ferramenta contra um perfil, com o esperado do
    registro de donos."""

    tipo: Literal["rota", "ferramenta"]
    nome: str
    perfil: Perfil
    esperado: Desfecho


def pares_da_matriz_completa() -> list[ParDaMatriz]:
    """Todas as rotas e todas as ferramentas contra os quatro perfis, lidas dos registros de
    donos: só o dono é permitido. Uma rota ou ferramenta nova entra sem mudar o comando."""

    def pares(tipo, donos: dict[str, Perfil]) -> list[ParDaMatriz]:
        return [
            ParDaMatriz(tipo, nome, perfil, "permitido" if donos[nome] is perfil else "negado")
            for nome in sorted(donos)
            for perfil in Perfil
        ]

    return pares("rota", DONO_DA_ROTA) + pares("ferramenta", DONO_DA_FERRAMENTA)


def _observar_ferramenta(resultado: CallToolResult) -> Observado:
    """O desfecho de uma chamada: sem erro é permitido; com erro é negado, e confere só se for a
    resposta de ferramenta inexistente, a mesma para quem não é dono (RS-08)."""
    if not resultado.is_error:
        return Observado("permitido", Resposta(status=None))
    mensagem = resultado.content[0].text if resultado.content else None
    return Observado(
        "negado",
        Resposta(status=None, mensagem=mensagem),
        confere=mensagem == FERRAMENTA_DESCONHECIDA,
    )


async def _chamadas_do_perfil(token: str, pares: list[ParDaMatriz]) -> list[Observado]:
    """As ferramentas dos pares chamadas numa sessão só do cliente MCP, com o token do perfil."""
    falha = Observado("negado", Resposta(status=None, mensagem="Falha ao chamar."), confere=False)
    try:
        async with Client(
            StreamableHttpTransport(MCP_DO_AMBIENTE + CAMINHO, auth=token)
        ) as cliente:
            observados = []
            for par in pares:
                try:
                    resultado = await cliente.call_tool(
                        par.nome, argumentos_minimos(par.nome), raise_on_error=False
                    )
                    observados.append(_observar_ferramenta(resultado))
                except Exception:
                    observados.append(falha)
            return observados
    except Exception:
        return [falha] * len(pares)


def _observar_par_de_rota(par: ParDaMatriz, contexto: Contexto) -> Observado:
    token = contexto.token_de(usuario_de(par.perfil).nome_de_usuario)
    try:
        resposta = contexto.api.get(par.nome, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError:
        return Observado("negado", Resposta(status=None), confere=False)
    return _observar_resposta(resposta, NEGACAO_DA_ROTA)


def executar_matriz_completa(
    contexto: Contexto,
    pares: list[ParDaMatriz] | None = None,
    andamento: Callable[[str], None] = print,
) -> MatrizCompleta:
    """Executa os pares, com os tokens e as sessões do cliente MCP reaproveitados (uma sessão por
    perfil), e conta os permitidos, os negados e as divergências. Um par divergente aparece no
    andamento; os demais, só na contagem."""
    pares = pares_da_matriz_completa() if pares is None else pares
    executada_em = datetime.now(UTC)
    observados: dict[ParDaMatriz, Observado] = {}
    for par in pares:
        if par.tipo == "rota":
            observados[par] = _observar_par_de_rota(par, contexto)
    for perfil in Perfil:
        do_perfil = [p for p in pares if p.tipo == "ferramenta" and p.perfil is perfil]
        if do_perfil:
            token = contexto.token_de(usuario_de(perfil).nome_de_usuario)
            chamadas = asyncio.run(_chamadas_do_perfil(token, do_perfil))
            observados |= zip(do_perfil, chamadas, strict=True)
    divergentes = [
        par
        for par, observado in observados.items()
        if observado.obtido != par.esperado or not observado.confere
    ]
    for par in divergentes:
        obtido = observados[par]
        andamento(
            f"  DIVERGÊNCIA na matriz: {par.perfil.value:<10} {par.nome:<32} "
            f"{obtido.obtido} ({obtido.resposta.status or '-'} {obtido.resposta.mensagem or ''}) "
            f"esperado {par.esperado}"
        )
    return MatrizCompleta(
        executada_em=executada_em,
        pares=len(observados),
        permitidos=sum(o.obtido == "permitido" for o in observados.values()),
        negados=sum(o.obtido == "negado" for o in observados.values()),
        divergencias=len(divergentes),
    )


# --- Execução ---


def executar_cenario(cenario: CenarioDeSeguranca, contexto: Contexto) -> Cenario:
    """Executa um cenário e o registra com o esperado, o obtido e a divergência. Uma falha ao
    executar não é escondida: vira um negado divergente, com o tipo da falha na mensagem."""
    inicio = time.perf_counter()
    try:
        cenario.preparar(contexto)
        inicio = time.perf_counter()
        observado = cenario.executar(contexto)
    except Exception as erro:
        falha = Resposta(status=None, mensagem=f"Falha ao executar ({type(erro).__name__}).")
        observado = Observado("negado", falha, confere=False)
    duracao = round((time.perf_counter() - inicio) * 1000)
    return Cenario(
        id=cenario.id,
        descricao=cenario.descricao,
        grupo=cenario.grupo,
        quem=cenario.quem,
        perfil=cenario.perfil,
        alvo=cenario.alvo,
        camadas_de_defesa=list(cenario.camadas_de_defesa),
        esperado=cenario.esperado,
        obtido=observado.obtido,
        divergencia=observado.obtido != cenario.esperado or not observado.confere,
        resposta=observado.resposta,
        auditoria=observado.auditoria,
        duracao_em_ms=duracao,
    )


def _linha_do_andamento(posicao: int, total: int, cenario: Cenario) -> str:
    marca = "DIVERGÊNCIA" if cenario.divergencia else "ok"
    resposta = cenario.resposta.status if cenario.resposta.status is not None else "-"
    return (
        f"[{posicao:>2}/{total}] {cenario.grupo:<20} {cenario.quem.nome:<16} "
        f"{cenario.alvo.nome:<32} {cenario.obtido:<9} ({resposta}) "
        f"esperado {cenario.esperado:<9} {cenario.duracao_em_ms:>5} ms  {marca}"
    )


def executar_aceite(
    lista: list[CenarioDeSeguranca],
    contexto: Contexto,
    andamento: Callable[[str], None] = print,
) -> ExecucaoDeAceite:
    """Executa os cenários em ordem, mostrando o andamento, e devolve a execução."""
    executada_em = datetime.now(UTC)
    executados = []
    for posicao, cenario in enumerate(lista, start=1):
        executado = executar_cenario(cenario, contexto)
        executados.append(executado)
        andamento(_linha_do_andamento(posicao, len(lista), executado))
    return ExecucaoDeAceite.dos_cenarios(executada_em, executados)


def _resumo(execucao: ExecucaoDeAceite, duracao: float) -> str:
    resumo = execucao.resumo
    return (
        f"{resumo.executados} executados, {resumo.permitidos} permitidos, "
        f"{resumo.negados} negados, {resumo.divergencias} divergências, em {duracao:.1f} s"
    )


def _resumo_da_matriz(matriz: MatrizCompleta) -> str:
    return (
        f"Matriz completa: {matriz.pares} pares, {matriz.permitidos} permitidos, "
        f"{matriz.negados} negados, {matriz.divergencias} divergências"
    )


def principal(
    argumentos: list[str] | None = None,
    lista: list[CenarioDeSeguranca] | None = None,
    escrever: Callable[[str], None] = print,
) -> int:
    """O comando: executa os cenários (por padrão, todos), mostra o andamento e o resumo com
    `escrever` e grava o resultado. Devolve o código de saída: 1 se algum cenário divergiu."""
    leitor = argparse.ArgumentParser(description="Execução de aceite: os cenários de segurança.")
    leitor.add_argument(
        "--pasta",
        type=Path,
        default=PASTA_PADRAO,
        help="onde gravar o resultado (padrão: backend/execucao-de-aceite)",
    )
    opcoes = leitor.parse_args(argumentos)
    inicio = time.perf_counter()
    lista = cenarios() if lista is None else lista
    escrever(f"Execução de aceite: {len(lista)} cenários de segurança contra {API}")
    with Contexto() as contexto:
        execucao = executar_aceite(lista, contexto, escrever)
        # A matriz completa cabe nos 2 minutos (medido no README): roda sempre, com a data dela.
        matriz = executar_matriz_completa(contexto, andamento=escrever)
    execucao = execucao.model_copy(update={"matriz_completa": matriz, "carga": conferir_carga()})
    escrever(_resumo_da_matriz(matriz))
    escrever(_linha_da_carga(execucao.carga))
    destino = gravar_execucao(execucao, opcoes.pasta)
    escrever(_resumo(execucao, time.perf_counter() - inicio))
    escrever(f"Resultado gravado em {destino}; recarregue o painel de segurança.")
    return 1 if execucao.resumo.divergencias or matriz.divergencias else 0


if __name__ == "__main__":
    # Acentos legíveis também quando a saída passa por um pipe no Windows.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(principal())
