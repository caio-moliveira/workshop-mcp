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
import os
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402
from apoio import banco_local, variavel  # noqa: E402
from provedor import USUARIOS_DE_DEMONSTRACAO, conteudo, token_pelo_fluxo_de_codigo  # noqa: E402
from registros import DONO_DA_ROTA  # noqa: E402

from aceite import (  # noqa: E402
    GRUPOS,
    Alvo,
    CamadaDeDefesa,
    Cenario,
    Desfecho,
    ExecucaoDeAceite,
    Grupo,
    LinhaDaAuditoria,
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


# Os cenários de cada grupo da matriz, na ordem em que um pedido atravessa as camadas de defesa.
# Um grupo ainda sem cenários fica de fora.
CENARIOS_POR_GRUPO: dict[Grupo, Callable[[], list[CenarioDeSeguranca]]] = {
    "api": cenarios_da_api,
}


def cenarios() -> list[CenarioDeSeguranca]:
    """Todos os cenários de segurança, agrupados pela camada de defesa."""
    return [
        cenario
        for grupo in GRUPOS
        if grupo in CENARIOS_POR_GRUPO
        for cenario in CENARIOS_POR_GRUPO[grupo]()
    ]


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
    destino = gravar_execucao(execucao, opcoes.pasta)
    escrever(_resumo(execucao, time.perf_counter() - inicio))
    escrever(f"Resultado gravado em {destino}; recarregue o painel de segurança.")
    return 1 if execucao.resumo.divergencias else 0


if __name__ == "__main__":
    # Acentos legíveis também quando a saída passa por um pipe no Windows.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(principal())
