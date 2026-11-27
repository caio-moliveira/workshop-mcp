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

Os cenários ficam agrupados pelo grupo da matriz (uma camada de defesa ou o assistente):
cada grupo tem a sua função em `CENARIOS_POR_GRUPO`.
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
import jwt  # noqa: E402
import psycopg  # noqa: E402
from apoio import (  # noqa: E402
    BANCO_DA_AUDITORIA,
    banco_local,
    conectar_como_dono,
    conectar_como_perfil,
    variavel,
)
from chaves_locais import nova_chave  # noqa: E402
from cliente_mcp import (  # noqa: E402
    CAMINHO,
    FERRAMENTA_DESCONHECIDA,
    MCP_DO_AMBIENTE,
    chamar,
    pedir_ao_protocolo,
)
from fabricas import api_no_processo  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.client.client import CallToolResult  # noqa: E402
from fastmcp.client.transports import StreamableHttpTransport  # noqa: E402
from provedor import (  # noqa: E402
    APLICACAO,
    OUTRA_APLICACAO,
    USUARIOS_DE_DEMONSTRACAO,
    conteudo,
    token_pelo_fluxo_de_codigo,
    usuario_de,
)
from pydantic_ai.messages import ModelRequest, ToolReturnPart  # noqa: E402
from registros import (  # noqa: E402
    DONO_DA_FERRAMENTA,
    DONO_DA_ROTA,
    argumentos_minimos,
    ferramentas_de,
)
from roteiro import eventos, modelo_roteirizado, perguntar  # noqa: E402
from starlette.applications import Starlette  # noqa: E402

from aceite import (  # noqa: E402
    GRUPOS,
    Alvo,
    CamadaDeDefesa,
    CenarioDeSeguranca,
    ConferenciaDaCarga,
    ContagemDeDesfechos,
    Desfecho,
    ExecucaoDeAceite,
    Grupo,
    LinhaDaAuditoria,
    MatrizCompleta,
    Quem,
    Resposta,
    gravar_execucao,
)
from acesso import Perfil, UsuarioAutenticado, mensagens  # noqa: E402
from auditoria import Resultado  # noqa: E402
from carga.configuracao import ler_configuracao  # noqa: E402
from consultas import Credencial, ExecutorDeConsultas, credenciais_do_ambiente  # noqa: E402
from historico import BANCO as BANCO_DO_HISTORICO  # noqa: E402
from historico import PAPEL as PAPEL_DO_HISTORICO  # noqa: E402
from historico import HistoricoNoBanco  # noqa: E402
from servidor_mcp.limite import CHAMADAS_PADRAO  # noqa: E402

API = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"
PASTA_PADRAO = Path(__file__).resolve().parents[1] / "execucao-de-aceite"

# O token de acesso vale 5 minutos; um token guardado é trocado bem antes de vencer.
VALIDADE_DO_TOKEN_GUARDADO_EM_SEGUNDOS = 3 * 60

# A negação esperada de cada pedido à API: o status e a mensagem.
NEGACAO_DA_ROTA = (403, mensagens.ACESSO_NEGADO)
NEGACAO_DA_CONVERSA = (404, mensagens.CONVERSA_INEXISTENTE)


@dataclass(frozen=True)
class Observado:
    """O que um cenário obteve. `confere` diz se a resposta tem a forma esperada além do
    desfecho: uma negação com outro status ou outra mensagem também é divergência."""

    obtido: Desfecho
    resposta: Resposta
    auditoria: LinhaDaAuditoria | None = None
    confere: bool = True


@dataclass(frozen=True)
class CenarioAExecutar:
    """A definição de um cenário de segurança: quem pede o quê, o esperado e como executá-lo.
    Executada, vira o `CenarioDeSeguranca` gravado no resultado."""

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

    def __init__(self, endereco_da_api: str = API, endereco_do_mcp: str = MCP_DO_AMBIENTE) -> None:
        self.api = httpx.Client(base_url=endereco_da_api, timeout=30)
        self.endereco_do_mcp = endereco_do_mcp
        self.mcp = httpx.Client(base_url=endereco_do_mcp, timeout=30)
        self._tokens: dict[tuple[str, str], tuple[str, float]] = {}
        self._historico: HistoricoNoBanco | None = None
        self._conversas: dict[str, tuple[UsuarioAutenticado, uuid.UUID]] = {}

    def token_de(self, nome_de_usuario: str, aplicacao: str = APLICACAO) -> str:
        """O token de acesso do usuário de demonstração, pelo fluxo de código, guardado. Por
        padrão, o login é o da aplicação; `aplicacao` escolhe outro cliente do realm."""
        chave = (nome_de_usuario, aplicacao)
        guardado = self._tokens.get(chave)
        if guardado and time.monotonic() - guardado[1] < VALIDADE_DO_TOKEN_GUARDADO_EM_SEGUNDOS:
            return guardado[0]
        senha = _usuario(nome_de_usuario).senha()
        token = token_pelo_fluxo_de_codigo(nome_de_usuario, senha, aplicacao)
        self._tokens[chave] = (token, time.monotonic())
        return token

    def usuario_autenticado(self, nome_de_usuario: str) -> UsuarioAutenticado:
        """O usuário de demonstração como a API o reconhece pelo token: o dono das conversas."""
        demonstracao = _usuario(nome_de_usuario)
        return UsuarioAutenticado(
            id=conteudo(self.token_de(nome_de_usuario))["sub"],
            nome=demonstracao.nome,
            perfil=demonstracao.perfil,
        )

    def conversa_de(self, nome_de_usuario: str) -> uuid.UUID:
        """Uma conversa do usuário, criada no histórico para a execução e apagada no fim."""
        if nome_de_usuario not in self._conversas:
            dono = self.usuario_autenticado(nome_de_usuario)
            identificador = self.historico().criar_conversa(
                dono, "Conversa da execução de aceite", uuid.uuid4()
            )
            self._conversas[nome_de_usuario] = (dono, identificador)
        return self._conversas[nome_de_usuario][1]

    def historico(self) -> HistoricoNoBanco:
        """O histórico das conversas do ambiente, aberto na primeira vez e fechado no fim."""
        if self._historico is None:
            banco = replace(banco_local(), nome=BANCO_DO_HISTORICO)
            credencial = Credencial(PAPEL_DO_HISTORICO, variavel("SENHA_DO_PAPEL_HISTORICO"))
            self._historico = HistoricoNoBanco(banco, credencial)
        return self._historico

    def fechar(self) -> None:
        for dono, identificador in self._conversas.values():
            self.historico().apagar_conversa(dono, identificador)
        if self._historico is not None:
            self._historico.fechar()
        self.api.close()
        self.mcp.close()

    def __enter__(self) -> "Contexto":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()


def _usuario(nome_de_usuario: str):
    return next(u for u in USUARIOS_DE_DEMONSTRACAO if u.nome_de_usuario == nome_de_usuario)


def _pedido_do_usuario(
    nome_de_usuario: str, *antes: Callable[["Contexto"], object]
) -> dict[str, object]:
    """Quem pede, o perfil e o `preparar` de um cenário pedido por um usuário de demonstração: o
    login dele e, antes, o que mais o cenário precisar (`antes`)."""

    def preparar(contexto: Contexto) -> None:
        for passo in antes:
            passo(contexto)
        contexto.token_de(nome_de_usuario)

    return {
        "quem": Quem(tipo="usuario", nome=nome_de_usuario),
        "perfil": _usuario(nome_de_usuario).perfil,
        "preparar": preparar,
    }


def _autorizacao(token: str) -> dict[str, str]:
    """O cabeçalho de autorização com o token."""
    return {"Authorization": f"Bearer {token}"}


def _esperado_pelo_dono(dono: Perfil | None, perfil: Perfil | None) -> Desfecho:
    """Só o dono, pelo registro de donos, é permitido."""
    return "permitido" if dono is not None and dono is perfil else "negado"


def _diverge(observado: Observado, esperado: Desfecho) -> bool:
    """Diverge o obtido diferente do esperado e a resposta sem a forma esperada."""
    return observado.obtido != esperado or not observado.confere


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


def leitura_de_rota(
    id: str,
    descricao: str,
    nome_de_usuario: str,
    rota: str,
    parametros: dict[str, str] | None = None,
) -> CenarioAExecutar:
    """Um usuário lê uma rota de dados da API; o esperado vem do registro de donos."""
    parametros = parametros or {}

    def executar(contexto: Contexto) -> Observado:
        token = contexto.token_de(nome_de_usuario)
        resposta = contexto.api.get(rota, headers=_autorizacao(token), params=parametros)
        return _observar_resposta(resposta, NEGACAO_DA_ROTA)

    return CenarioAExecutar(
        id=id,
        descricao=descricao,
        grupo="api",
        **_pedido_do_usuario(nome_de_usuario),
        alvo=Alvo(tipo="rota", nome=rota, parametros=parametros),
        camadas_de_defesa=("api",),
        esperado=_esperado_pelo_dono(DONO_DA_ROTA[rota], _usuario(nome_de_usuario).perfil),
        executar=executar,
    )


def leitura_da_conversa_de_outro(
    id: str, descricao: str, nome_de_usuario: str, dono_da_conversa: str
) -> CenarioAExecutar:
    """Um usuário lê a conversa de outro: responde como uma conversa que não existe (RF-18)."""

    def executar(contexto: Contexto) -> Observado:
        identificador = contexto.conversa_de(dono_da_conversa)
        token = contexto.token_de(nome_de_usuario)
        resposta = contexto.api.get(f"/conversas/{identificador}", headers=_autorizacao(token))
        return _observar_resposta(resposta, NEGACAO_DA_CONVERSA)

    return CenarioAExecutar(
        id=id,
        descricao=descricao,
        grupo="api",
        **_pedido_do_usuario(nome_de_usuario, lambda c: c.conversa_de(dono_da_conversa)),
        alvo=Alvo(
            tipo="conversa",
            nome="/conversas/{id_da_conversa}",
            parametros={"dono": dono_da_conversa},
        ),
        camadas_de_defesa=("api",),
        # Só o dono alcança a própria conversa.
        esperado="permitido" if nome_de_usuario == dono_da_conversa else "negado",
        executar=executar,
    )


def cenarios_da_api() -> list[CenarioAExecutar]:
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


# --- Servidor MCP: camadas de defesa Token, Lista de ferramentas e Chamada ---

FERRAMENTA_QUE_NUNCA_EXISTIU = "vendas_margem_por_cliente"
LISTA_DE_FERRAMENTAS = "tools/list"


def _token_forjado(token: str) -> str:
    """O mesmo cabeçalho e o mesmo conteúdo de um token real, assinados por uma chave que o
    provedor não conhece: só a assinatura é falsa."""
    cabecalho = jwt.get_unverified_header(token)
    return jwt.encode(conteudo(token), nova_chave(), algorithm="RS256", headers=cabecalho)


def _observar_recusa_do_token(resposta: httpx.Response) -> Observado:
    """A recusa do token no servidor MCP: 401, sem corpo, com o `WWW-Authenticate` Bearer."""
    if resposta.is_success:
        return Observado("permitido", Resposta(status=resposta.status_code), confere=False)
    bearer = resposta.headers.get("www-authenticate", "").startswith("Bearer")
    return Observado(
        "negado",
        Resposta(status=resposta.status_code),
        confere=resposta.status_code == 401 and bearer,
    )


def _ferramentas_listadas(resposta: httpx.Response) -> list[str] | None:
    """Os nomes que o servidor listou; `None` se a lista não veio."""
    if not resposta.is_success:
        return None
    return sorted(f["name"] for f in resposta.json()["result"]["tools"])


def recusa_do_token(
    id: str,
    descricao: str,
    tipo_de_token: str,
    obter_token: Callable[["Contexto"], str | None],
) -> CenarioAExecutar:
    """A lista de ferramentas pedida com um token que o servidor MCP não pode aceitar."""
    tokens: dict[str, str | None] = {}

    def preparar(contexto: Contexto) -> None:
        tokens["token"] = obter_token(contexto)

    def executar(contexto: Contexto) -> Observado:
        resposta = pedir_ao_protocolo(contexto.mcp, tokens["token"], LISTA_DE_FERRAMENTAS)
        return _observar_recusa_do_token(resposta)

    return CenarioAExecutar(
        id=id,
        descricao=descricao,
        grupo="token",
        quem=Quem(tipo="token", nome=tipo_de_token),
        perfil=None,
        alvo=Alvo(tipo="lista_de_ferramentas", nome=LISTA_DE_FERRAMENTAS),
        camadas_de_defesa=("token",),
        esperado="negado",
        executar=executar,
        preparar=preparar,
    )


def lista_de_ferramentas(id: str, descricao: str, nome_de_usuario: str) -> CenarioAExecutar:
    """O usuário lista as ferramentas e precisa ver exatamente as do perfil, pelo registro. Só a
    quantidade vai para o resultado."""
    perfil = _usuario(nome_de_usuario).perfil

    def executar(contexto: Contexto) -> Observado:
        token = contexto.token_de(nome_de_usuario)
        resposta = pedir_ao_protocolo(contexto.mcp, token, LISTA_DE_FERRAMENTAS)
        listadas = _ferramentas_listadas(resposta)
        if listadas is None:
            return Observado("negado", Resposta(status=resposta.status_code), confere=False)
        return Observado(
            "permitido",
            Resposta(status=resposta.status_code, linhas=len(listadas)),
            confere=listadas == ferramentas_de(perfil),
        )

    return CenarioAExecutar(
        id=id,
        descricao=descricao,
        grupo="lista_de_ferramentas",
        **_pedido_do_usuario(nome_de_usuario),
        alvo=Alvo(tipo="lista_de_ferramentas", nome=LISTA_DE_FERRAMENTAS),
        camadas_de_defesa=("lista_de_ferramentas",),
        esperado="permitido",
        executar=executar,
    )


def _mensagem_do_erro(resultado: CallToolResult) -> str | None:
    """A mensagem de um erro de ferramenta: o único texto do conteúdo; `None` se houver outra
    coisa (nenhum texto ou mais de um)."""
    textos = [getattr(item, "text", None) for item in resultado.content]
    return textos[0] if len(textos) == 1 else None


def _desfecho_da_chamada(resultado: CallToolResult) -> tuple[Desfecho, Resposta]:
    """O desfecho de uma chamada de ferramenta, sem status: o resultado de uma ferramenta não é
    um status HTTP. O erro de ferramenta é negado, com a mensagem; o sucesso é permitido, só com
    a quantidade de linhas."""
    if resultado.is_error:
        return "negado", Resposta(status=None, mensagem=_mensagem_do_erro(resultado))
    return "permitido", Resposta(status=None, linhas=_linhas(resultado.structured_content))


def _resultado_na_auditoria(obtido: Desfecho) -> Resultado:
    """O desfecho que a chamada precisa deixar na auditoria."""
    return Resultado.PERMITIDA if obtido == "permitido" else Resultado.NEGADA


def _camadas_da_ferramenta(dono: Perfil | None, perfil: Perfil) -> tuple[CamadaDeDefesa, ...]:
    """As camadas que barram a chamada a uma ferramenta. A de outro perfil existe e some da lista
    do token, e a chamada a ela é recusada; a do perfil e a inexistente (que nem existe para
    sumir) só passam pela chamada."""
    if dono is not None and dono is not perfil:
        return ("lista_de_ferramentas", "chamada")
    return ("chamada",)


def chamada_de_ferramenta(
    id: str, descricao: str, nome_de_usuario: str, ferramenta: str
) -> CenarioAExecutar:
    """O usuário chama uma ferramenta com os argumentos mínimos dela; o esperado vem do registro
    de donos. A de outro perfil é barrada em duas camadas, e o cenário confere as duas: ela não
    aparece na lista e é recusada na chamada. A negação é a da ferramenta inexistente, e a linha
    da auditoria precisa trazer o desfecho (CA-07)."""
    perfil = _usuario(nome_de_usuario).perfil
    dono = DONO_DA_FERRAMENTA.get(ferramenta)
    argumentos = argumentos_minimos(ferramenta) if dono else {}
    camadas = _camadas_da_ferramenta(dono, perfil)

    def executar(contexto: Contexto) -> Observado:
        token = contexto.token_de(nome_de_usuario)
        antes = _ultimo_id_da_auditoria()
        fora_da_lista = True
        if "lista_de_ferramentas" in camadas:
            listadas = _ferramentas_listadas(
                pedir_ao_protocolo(contexto.mcp, token, LISTA_DE_FERRAMENTAS)
            )
            fora_da_lista = listadas is not None and ferramenta not in listadas
        resultado = chamar(contexto.endereco_do_mcp, token, ferramenta, argumentos)
        obtido, observada = _desfecho_da_chamada(resultado)
        # A linha da chamada do cenário: a da ferramenta, entre as do usuário depois do marco.
        linhas = _linhas_da_auditoria_desde(conteudo(token)["sub"], antes)
        auditoria = next((linha for linha in linhas if linha.ferramenta == ferramenta), None)
        mensagem_certa = obtido == "permitido" or observada.mensagem == FERRAMENTA_DESCONHECIDA
        auditada = auditoria is not None and auditoria.resultado == _resultado_na_auditoria(obtido)
        confere = fora_da_lista and mensagem_certa and auditada
        return Observado(obtido, observada, auditoria, confere)

    return CenarioAExecutar(
        id=id,
        descricao=descricao,
        grupo="chamada",
        **_pedido_do_usuario(nome_de_usuario),
        alvo=Alvo(tipo="ferramenta", nome=ferramenta, parametros=argumentos),
        camadas_de_defesa=camadas,
        esperado=_esperado_pelo_dono(dono, perfil),
        executar=executar,
    )


def cenarios_do_token() -> list[CenarioAExecutar]:
    return [
        recusa_do_token(
            "token-sem-token",
            "Sem token, o servidor MCP recusa o pedido",
            "sem token",
            lambda _: None,
        ),
        recusa_do_token(
            "token-de-outra-aplicacao",
            "O token de outra aplicação do mesmo provedor é recusado (CA-03)",
            "token de outra aplicação",
            lambda contexto: contexto.token_de("ana.vendas", OUTRA_APLICACAO),
        ),
        recusa_do_token(
            "token-com-assinatura-forjada",
            "Um token com a assinatura forjada é recusado",
            "token com assinatura forjada",
            lambda contexto: _token_forjado(contexto.token_de("ana.vendas")),
        ),
    ]


def cenarios_da_lista_de_ferramentas() -> list[CenarioAExecutar]:
    return [
        lista_de_ferramentas(
            "lista-de-vendas", "Vendas lista só as próprias ferramentas", "ana.vendas"
        ),
        lista_de_ferramentas(
            "lista-de-produtos", "Produtos lista só as próprias ferramentas", "bruno.produtos"
        ),
        lista_de_ferramentas(
            "lista-do-comercial", "O Comercial lista só as próprias ferramentas", "carla.comercial"
        ),
        lista_de_ferramentas(
            "lista-da-diretoria", "A Diretoria lista só as próprias ferramentas", "diego.diretoria"
        ),
    ]


def cenarios_da_chamada() -> list[CenarioAExecutar]:
    return [
        chamada_de_ferramenta(
            "chamada-dono-chama-a-propria-ferramenta",
            "O dono chama a própria ferramenta, e a chamada fica na auditoria",
            "ana.vendas",
            ferramentas_de(Perfil.VENDAS)[0],
        ),
        chamada_de_ferramenta(
            "chamada-vendas-chama-ferramenta-da-diretoria",
            "Vendas chama uma ferramenta da Diretoria: não listada e recusada",
            "ana.vendas",
            ferramentas_de(Perfil.DIRETORIA)[0],
        ),
        chamada_de_ferramenta(
            "chamada-diretoria-chama-ferramenta-de-vendas",
            "A Diretoria chama uma ferramenta de Vendas: não listada e recusada",
            "diego.diretoria",
            ferramentas_de(Perfil.VENDAS)[0],
        ),
        chamada_de_ferramenta(
            "chamada-ferramenta-inexistente",
            "Uma ferramenta inexistente recebe a mesma resposta da de outro perfil",
            "ana.vendas",
            FERRAMENTA_QUE_NUNCA_EXISTIU,
        ),
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
) -> CenarioAExecutar:
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
    return CenarioAExecutar(
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


def cenarios_do_banco() -> list[CenarioAExecutar]:
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
) -> CenarioAExecutar:
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
        obtido, observada = _desfecho_da_chamada(resultado)
        if obtido == "negado":
            limitada = ultima is not None and ultima.resultado == Resultado.LIMITADA
            return Observado(
                obtido,
                observada,
                ultima,
                confere=limitada and observada.mensagem == mensagens.MUITAS_CHAMADAS,
            )
        return Observado(
            obtido,
            observada,
            ultima,
            confere=ultima is not None and ultima.resultado == Resultado.PERMITIDA,
        )

    return CenarioAExecutar(
        id=id,
        descricao=descricao,
        grupo="limite_de_frequencia",
        **_pedido_do_usuario(nome_de_usuario),
        alvo=Alvo(
            tipo="ferramenta",
            nome=FERRAMENTA_DO_LIMITE,
            parametros={**ARGUMENTOS_DO_LIMITE, "chamadas": chamadas},
        ),
        camadas_de_defesa=("limite_de_frequencia",),
        esperado=esperado,
        executar=executar,
        exige_limite_padrao=True,
    )


def cenarios_do_limite(servidor: str | Starlette = MCP_DO_AMBIENTE) -> list[CenarioAExecutar]:
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


def _recusa_de_ferramenta_desconhecida(retorno: ToolReturnPart) -> bool:
    """A recusa que o assistente devolve ao modelo quando ele pede um nome que o servidor MCP não
    listou para o token: uma nova tentativa por ferramenta desconhecida, sem chegar ao servidor.

    O texto dela ("Unknown tool name: ... Available tools: ...") cita as ferramentas do perfil;
    por isso o cenário grava, no lugar dele, a mensagem genérica da ferramenta desconhecida."""
    return (
        retorno.outcome == "retried"
        and retorno.retry is not None
        and retorno.retry.cause == "unknown_tool"
    )


def pergunta_ao_assistente(
    id: str,
    descricao: str,
    nome_de_usuario: str,
    ferramenta: str,
    argumentos: dict[str, str] | None = None,
) -> CenarioAExecutar:
    """O usuário pergunta ao assistente, e o modelo roteirizado chama a ferramenta dada, por padrão
    com os argumentos mínimos dela. O esperado vem do registro de donos das ferramentas."""
    perfil = _usuario(nome_de_usuario).perfil
    dono = DONO_DA_FERRAMENTA[ferramenta]
    argumentos = argumentos or {**argumentos_minimos(ferramenta), "periodo": "30d"}

    def executar(contexto: Contexto) -> Observado:
        token = contexto.token_de(nome_de_usuario)
        do_token = conteudo(token)
        historico = contexto.historico()
        vistos: dict = {}
        modelo = modelo_roteirizado(
            chamadas=[(ferramenta, argumentos)], pedacos=["Ok."], vistos=vistos
        )
        antes = _ultimo_id_da_auditoria()
        with ExecutorDeConsultas(banco_local(), credenciais_do_ambiente()) as consultas:
            api = api_no_processo(consultas, historico, modelo, contexto.endereco_do_mcp + CAMINHO)
            resposta = perguntar(api, token, {"pergunta": PERGUNTA_AO_ASSISTENTE})
            lidos = eventos(resposta)
        # A conversa da pergunta é só da execução: sai do histórico.
        historico.apagar_conversa(
            contexto.usuario_autenticado(nome_de_usuario),
            uuid.UUID(lidos[0][1]["id_da_conversa"]),
        )

        linhas = _linhas_da_auditoria_desde(do_token["sub"], antes)
        retornos = [
            parte
            for mensagem in vistos.get("mensagens", [])
            if isinstance(mensagem, ModelRequest)
            for parte in mensagem.parts
            if isinstance(parte, ToolReturnPart) and parte.tool_name == ferramenta
        ]
        sucesso = next((r for r in retornos if r.outcome == "success"), None)
        if sucesso:
            [linha] = linhas or [None]
            return Observado(
                "permitido",
                Resposta(status=resposta.status_code, linhas=_linhas(sucesso.content)),
                linha,
                confere=len(linhas) == 1
                and linha.usuario == do_token["name"]
                and linha.ferramenta == ferramenta
                and linha.resultado == Resultado.PERMITIDA,
            )
        recusada = any(_recusa_de_ferramenta_desconhecida(r) for r in retornos)
        return Observado(
            "negado",
            # O 200 é o do `/assistente`, que respondeu à pergunta; a negação, como nas
            # ferramentas, não tem status.
            Resposta(
                status=None,
                mensagem=mensagens.FERRAMENTA_DESCONHECIDA if recusada else None,
            ),
            # Recusada antes do servidor: nenhuma linha nova na auditoria. Qualquer outra falha
            # (o servidor fora do ar, um argumento inválido) não é a negação esperada.
            confere=recusada and not linhas,
        )

    return CenarioAExecutar(
        id=id,
        descricao=descricao,
        grupo="assistente",
        **_pedido_do_usuario(nome_de_usuario),
        alvo=Alvo(
            tipo="assistente",
            nome="/assistente",
            parametros={"ferramenta": ferramenta, **argumentos},
        ),
        # O assistente só conhece as ferramentas que a lista do token devolveu, e a tentativa de
        # outra é recusada ao ser chamada.
        camadas_de_defesa=_camadas_da_ferramenta(dono, perfil),
        esperado=_esperado_pelo_dono(dono, perfil),
        executar=executar,
    )


def cenarios_do_assistente() -> list[CenarioAExecutar]:
    return [
        pergunta_ao_assistente(
            "assistente-chama-o-mcp-com-o-token-do-usuario",
            "O assistente chama o servidor MCP com o token do usuário (RF-15)",
            "bruno.produtos",
            "produtos_indicadores",
        ),
        pergunta_ao_assistente(
            "assistente-ferramenta-de-outro-perfil",
            "O modelo tenta uma ferramenta de outro perfil: não listada e recusada",
            "bruno.produtos",
            "comercial_indicadores",
        ),
    ]


# Os cenários de cada grupo da matriz.
CENARIOS_POR_GRUPO: dict[Grupo, Callable[[], list[CenarioAExecutar]]] = {
    "token": cenarios_do_token,
    "lista_de_ferramentas": cenarios_da_lista_de_ferramentas,
    "chamada": cenarios_da_chamada,
    "api": cenarios_da_api,
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


def cenarios() -> list[CenarioAExecutar]:
    """Todos os cenários de segurança, por grupo, na ordem em que um pedido atravessa as camadas
    de defesa."""
    return [cenario for grupo in GRUPOS for cenario in CENARIOS_POR_GRUPO[grupo]()]


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
            ParDaMatriz(tipo, nome, perfil, _esperado_pelo_dono(donos[nome], perfil))
            for nome in sorted(donos)
            for perfil in Perfil
        ]

    return pares("rota", DONO_DA_ROTA) + pares("ferramenta", DONO_DA_FERRAMENTA)


def _observar_ferramenta(resultado: CallToolResult) -> Observado:
    """O desfecho de uma chamada: sem erro é permitido; com erro é negado, e confere só se for a
    resposta de ferramenta inexistente, a mesma para quem não é dono (RS-08)."""
    obtido, observada = _desfecho_da_chamada(resultado)
    if obtido == "permitido":
        return Observado(obtido, Resposta(status=None))
    return Observado(obtido, observada, confere=observada.mensagem == FERRAMENTA_DESCONHECIDA)


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
        resposta = contexto.api.get(par.nome, headers=_autorizacao(token))
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
        par for par, observado in observados.items() if _diverge(observado, par.esperado)
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
        **ContagemDeDesfechos.contar(
            (observado.obtido, par in divergentes) for par, observado in observados.items()
        ),
    )


# --- Execução ---


def executar_cenario(cenario: CenarioAExecutar, contexto: Contexto) -> CenarioDeSeguranca:
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
    return CenarioDeSeguranca(
        id=cenario.id,
        descricao=cenario.descricao,
        grupo=cenario.grupo,
        quem=cenario.quem,
        perfil=cenario.perfil,
        alvo=cenario.alvo,
        camadas_de_defesa=list(cenario.camadas_de_defesa),
        esperado=cenario.esperado,
        obtido=observado.obtido,
        divergencia=_diverge(observado, cenario.esperado),
        resposta=observado.resposta,
        auditoria=observado.auditoria,
        duracao_em_ms=duracao,
    )


def _linha_do_andamento(posicao: int, total: int, cenario: CenarioDeSeguranca) -> str:
    marca = "DIVERGÊNCIA" if cenario.divergencia else "ok"
    resposta = cenario.resposta.status if cenario.resposta.status is not None else "-"
    return (
        f"[{posicao:>2}/{total}] {cenario.grupo:<20} {cenario.quem.nome:<16} "
        f"{cenario.alvo.nome:<32} {cenario.obtido:<9} ({resposta}) "
        f"esperado {cenario.esperado:<9} {cenario.duracao_em_ms:>5} ms  {marca}"
    )


def executar_aceite(
    cenarios_a_executar: list[CenarioAExecutar],
    contexto: Contexto,
    andamento: Callable[[str], None] = print,
) -> ExecucaoDeAceite:
    """Executa os cenários em ordem, mostrando o andamento, e devolve a execução."""
    executada_em = datetime.now(UTC)
    executados = []
    total = len(cenarios_a_executar)
    for posicao, cenario in enumerate(cenarios_a_executar, start=1):
        executado = executar_cenario(cenario, contexto)
        executados.append(executado)
        andamento(_linha_do_andamento(posicao, total, executado))
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
    cenarios_a_executar: list[CenarioAExecutar] | None = None,
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
    if cenarios_a_executar is None:
        cenarios_a_executar = cenarios()
    escrever(f"Execução de aceite: {len(cenarios_a_executar)} cenários de segurança contra {API}")
    with Contexto() as contexto:
        execucao = executar_aceite(cenarios_a_executar, contexto, escrever)
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
