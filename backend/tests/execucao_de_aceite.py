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
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402
import jwt  # noqa: E402
from apoio import BANCO_DA_AUDITORIA, banco_local, conectar_como_dono, variavel  # noqa: E402
from chaves_locais import nova_chave  # noqa: E402
from cliente_mcp import (  # noqa: E402
    CAMINHO,
    FERRAMENTA_DESCONHECIDA,
    MCP_DO_AMBIENTE,
    pedir_ao_protocolo,
)
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
from registros import (  # noqa: E402
    DONO_DA_FERRAMENTA,
    DONO_DA_ROTA,
    argumentos_minimos,
    ferramentas_de,
)

from aceite import (  # noqa: E402
    GRUPOS,
    Alvo,
    CamadaDeDefesa,
    Cenario,
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
from consultas import Credencial  # noqa: E402
from historico import BANCO as BANCO_DO_HISTORICO  # noqa: E402
from historico import PAPEL as PAPEL_DO_HISTORICO  # noqa: E402
from historico import HistoricoNoBanco  # noqa: E402

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

    def __init__(self, endereco_da_api: str = API, endereco_do_mcp: str = MCP_DO_AMBIENTE) -> None:
        self.api = httpx.Client(base_url=endereco_da_api, timeout=30)
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
        self.mcp.close()

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
) -> CenarioDeSeguranca:
    """A lista de ferramentas pedida com um token que o servidor MCP não pode aceitar."""
    tokens: dict[str, str | None] = {}

    def preparar(contexto: Contexto) -> None:
        tokens["token"] = obter_token(contexto)

    def executar(contexto: Contexto) -> Observado:
        resposta = pedir_ao_protocolo(contexto.mcp, tokens["token"], LISTA_DE_FERRAMENTAS)
        return _observar_recusa_do_token(resposta)

    return CenarioDeSeguranca(
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


def lista_de_ferramentas(id: str, descricao: str, nome_de_usuario: str) -> CenarioDeSeguranca:
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

    return CenarioDeSeguranca(
        id=id,
        descricao=descricao,
        grupo="lista_de_ferramentas",
        quem=Quem(tipo="usuario", nome=nome_de_usuario),
        perfil=perfil,
        alvo=Alvo(tipo="lista_de_ferramentas", nome=LISTA_DE_FERRAMENTAS),
        camadas_de_defesa=("lista_de_ferramentas",),
        esperado="permitido",
        executar=executar,
        preparar=lambda contexto: contexto.token_de(nome_de_usuario),
    )


def _ultimo_id_da_auditoria(id_do_usuario: str) -> int:
    """O id da linha mais recente do usuário na auditoria, lido pelo dono; 0 se não há."""
    with conectar_como_dono(BANCO_DA_AUDITORIA) as conexao:
        (ultimo,) = conexao.execute(
            "select coalesce(max(id), 0) from auditoria.chamada where id_do_usuario = %s",
            (id_do_usuario,),
        ).fetchone()
    return ultimo


def _linha_da_auditoria(
    id_do_usuario: str, ferramenta: str, depois_de: int
) -> LinhaDaAuditoria | None:
    """A linha que a chamada deixou na auditoria, lida pelo dono: a primeira do usuário para a
    ferramenta depois de `depois_de`. O filtro isola a chamada do cenário das de outros pedidos
    do mesmo usuário."""
    with conectar_como_dono(BANCO_DA_AUDITORIA) as conexao:
        linha = conexao.execute(
            "select id, horario, nome_do_usuario, ferramenta, parametros, resultado"
            " from auditoria.chamada where id_do_usuario = %s and ferramenta = %s and id > %s"
            " order by id limit 1",
            (id_do_usuario, ferramenta, depois_de),
        ).fetchone()
    if linha is None:
        return None
    id, horario, usuario, nome, argumentos, resultado = linha
    return LinhaDaAuditoria(
        id=id,
        horario=horario,
        usuario=usuario,
        ferramenta=nome,
        argumentos=argumentos,
        resultado=resultado,
    )


def _observar_chamada(resposta: httpx.Response) -> tuple[Desfecho, Resposta]:
    """O desfecho de uma chamada de ferramenta: o erro de ferramenta é negado, com a mensagem; o
    sucesso é permitido, só com o status e a quantidade de linhas."""
    resultado = resposta.json().get("result", {}) if resposta.is_success else {}
    if resposta.is_success and not resultado.get("isError"):
        linhas = _linhas(resultado.get("structuredContent"))
        return "permitido", Resposta(status=resposta.status_code, linhas=linhas)
    textos = [item.get("text") for item in resultado.get("content", [])]
    mensagem = textos[0] if len(textos) == 1 else None
    return "negado", Resposta(status=resposta.status_code, mensagem=mensagem)


def chamada_de_ferramenta(
    id: str, descricao: str, nome_de_usuario: str, ferramenta: str
) -> CenarioDeSeguranca:
    """O usuário chama uma ferramenta com os argumentos mínimos dela; o esperado vem do registro
    de donos. A de outro perfil é barrada em duas camadas, e o cenário confere as duas: ela não
    aparece na lista e é recusada na chamada. A negação é a da ferramenta inexistente, e a linha
    da auditoria precisa trazer o desfecho (CA-07)."""
    perfil = _usuario(nome_de_usuario).perfil
    dono = DONO_DA_FERRAMENTA.get(ferramenta)
    esperado: Desfecho = "permitido" if dono is perfil else "negado"
    argumentos = argumentos_minimos(ferramenta) if dono else {}
    # A de outro perfil existe e some da lista; a inexistente nem existe para sumir.
    de_outro_perfil = dono is not None and dono is not perfil
    camadas: tuple[CamadaDeDefesa, ...] = (
        ("lista_de_ferramentas", "chamada") if de_outro_perfil else ("chamada",)
    )
    antes: dict[str, int] = {}

    def preparar(contexto: Contexto) -> None:
        sub = conteudo(contexto.token_de(nome_de_usuario))["sub"]
        antes["id"] = _ultimo_id_da_auditoria(sub)

    def executar(contexto: Contexto) -> Observado:
        token = contexto.token_de(nome_de_usuario)
        fora_da_lista = True
        if de_outro_perfil:
            listadas = _ferramentas_listadas(
                pedir_ao_protocolo(contexto.mcp, token, LISTA_DE_FERRAMENTAS)
            )
            fora_da_lista = listadas is not None and ferramenta not in listadas
        chamada = {"name": ferramenta, "arguments": argumentos}
        resposta = pedir_ao_protocolo(contexto.mcp, token, "tools/call", chamada)
        obtido, observada = _observar_chamada(resposta)
        auditoria = _linha_da_auditoria(conteudo(token)["sub"], ferramenta, antes["id"])
        mensagem_certa = obtido == "permitido" or observada.mensagem == FERRAMENTA_DESCONHECIDA
        na_auditoria = "permitida" if obtido == "permitido" else "negada"
        auditada = auditoria is not None and auditoria.resultado == na_auditoria
        confere = fora_da_lista and mensagem_certa and auditada
        return Observado(obtido, observada, auditoria, confere)

    return CenarioDeSeguranca(
        id=id,
        descricao=descricao,
        grupo="chamada",
        quem=Quem(tipo="usuario", nome=nome_de_usuario),
        perfil=perfil,
        alvo=Alvo(tipo="ferramenta", nome=ferramenta, parametros=argumentos),
        camadas_de_defesa=camadas,
        esperado=esperado,
        executar=executar,
        preparar=preparar,
    )


def cenarios_do_token() -> list[CenarioDeSeguranca]:
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


def cenarios_da_lista_de_ferramentas() -> list[CenarioDeSeguranca]:
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


def cenarios_da_chamada() -> list[CenarioDeSeguranca]:
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


# Os cenários de cada grupo da matriz, na ordem em que um pedido atravessa as camadas de defesa.
# Um grupo ainda sem cenários fica de fora.
CENARIOS_POR_GRUPO: dict[Grupo, Callable[[], list[CenarioDeSeguranca]]] = {
    "api": cenarios_da_api,
    "token": cenarios_do_token,
    "lista_de_ferramentas": cenarios_da_lista_de_ferramentas,
    "chamada": cenarios_da_chamada,
}


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
    execucao = execucao.model_copy(update={"matriz_completa": matriz})
    escrever(_resumo_da_matriz(matriz))
    destino = gravar_execucao(execucao, opcoes.pasta)
    escrever(_resumo(execucao, time.perf_counter() - inicio))
    escrever(f"Resultado gravado em {destino}; recarregue o painel de segurança.")
    return 1 if execucao.resumo.divergencias or matriz.divergencias else 0


if __name__ == "__main__":
    # Acentos legíveis também quando a saída passa por um pipe no Windows.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(principal())
