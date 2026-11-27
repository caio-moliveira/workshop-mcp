"""A forma do resultado de uma execução de aceite, como ele é gravado e como a API o devolve.

Tudo o que sai para o painel de segurança passa por estes modelos, e só o que eles declaram sai:
um campo a mais no arquivo (um token, o corpo de uma resposta) fica para trás na leitura. Por
isso nenhum deles tem lugar para token, segredo ou dado de negócio; um cenário permitido traz só
o status e a quantidade de linhas.
"""

import os
import tempfile
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, get_args

from pydantic import BaseModel, PlainSerializer, model_validator

from acesso import Perfil

# O arquivo da última execução, dentro da pasta da execução de aceite. Cada execução o substitui.
ARQUIVO_DA_ULTIMA_EXECUCAO = "ultima-execucao.json"

# Os pontos que podem barrar um pedido, na ordem em que um pedido os atravessa (glossário).
CamadaDeDefesa = Literal[
    "token", "lista_de_ferramentas", "chamada", "api", "banco", "limite_de_frequencia"
]
CAMADAS_DE_DEFESA: tuple[CamadaDeDefesa, ...] = get_args(CamadaDeDefesa)

# Os grupos da matriz do painel: um por camada de defesa e mais o do assistente, cujos cenários
# a Chamada barra.
Grupo = Literal[
    "token",
    "lista_de_ferramentas",
    "chamada",
    "api",
    "banco",
    "limite_de_frequencia",
    "assistente",
]
GRUPOS: tuple[Grupo, ...] = get_args(Grupo)

Desfecho = Literal["permitido", "negado"]

# A data como `isoformat()`, com o fuso em `+00:00`, como nas outras rotas da API.
Horario = Annotated[datetime, PlainSerializer(datetime.isoformat, return_type=str)]


class ContagemDeDesfechos(BaseModel):
    """Quantos foram permitidos, quantos negados e quantos deram um resultado diferente do
    esperado."""

    permitidos: int
    negados: int
    divergencias: int

    @staticmethod
    def contar(desfechos: Iterable[tuple[Desfecho, bool]]) -> dict[str, int]:
        """Os três campos, contados dos pares (obtido, divergência)."""
        lidos = list(desfechos)
        return {
            "permitidos": sum(obtido == "permitido" for obtido, _ in lidos),
            "negados": sum(obtido == "negado" for obtido, _ in lidos),
            "divergencias": sum(divergencia for _, divergencia in lidos),
        }


class Contagem(ContagemDeDesfechos):
    """O resumo de uma execução: os cenários executados, os permitidos, os negados e as
    divergências."""

    executados: int


class MatrizCompleta(ContagemDeDesfechos):
    """Todos os pares de rotas e de ferramentas contra os quatro perfis, com a data própria: ela
    pode ter rodado numa execução anterior."""

    executada_em: Horario
    pares: int


class ConferenciaDaCarga(BaseModel):
    """Se o banco está no estado da carga: a data de referência e as contagens de referência."""

    confere: bool
    data_de_referencia: date | None = None
    detalhe: str | None = None


class Quem(BaseModel):
    """Quem pede: um usuário de demonstração, um papel do banco ou um tipo de token (sem o
    token)."""

    tipo: Literal["usuario", "papel", "token"]
    nome: str


class Alvo(BaseModel):
    """O que é pedido: uma rota, uma ferramenta, a lista de ferramentas, uma camada de leitura,
    os dados de origem, uma conversa ou o assistente; com os parâmetros do pedido."""

    tipo: Literal[
        "rota",
        "ferramenta",
        "lista_de_ferramentas",
        "camada_de_leitura",
        "dados_de_origem",
        "conversa",
        "assistente",
    ]
    nome: str
    parametros: dict[str, str | int] = {}


class Resposta(BaseModel):
    """A resposta obtida: o status (HTTP, quando há), a mensagem da negação e, no permitido, a
    quantidade de linhas. A mensagem de um permitido é descartada: poderia ser dado de negócio."""

    status: int | None
    mensagem: str | None = None
    linhas: int | None = None


class LinhaDaAuditoria(BaseModel):
    """A linha que a chamada deixou na auditoria, lida pelo dono (CA-07)."""

    id: int
    horario: Horario
    usuario: str
    ferramenta: str
    argumentos: dict[str, Any] | None
    resultado: str


class CenarioDeSeguranca(BaseModel):
    """Um cenário de segurança executado, como fica gravado: o esperado, o obtido e a
    divergência."""

    id: str
    descricao: str
    grupo: Grupo
    quem: Quem
    perfil: Perfil | None
    alvo: Alvo
    camadas_de_defesa: list[CamadaDeDefesa]
    esperado: Desfecho
    obtido: Desfecho
    divergencia: bool
    resposta: Resposta
    auditoria: LinhaDaAuditoria | None = None
    duracao_em_ms: int

    @model_validator(mode="after")
    def _permitido_sem_mensagem(self) -> "CenarioDeSeguranca":
        if self.obtido == "permitido":
            self.resposta.mensagem = None
        return self


class ExecucaoDeAceite(BaseModel):
    """Uma execução de aceite: a data, o resumo, a matriz completa, a conferência da carga e os
    cenários."""

    executada_em: Horario
    resumo: Contagem
    matriz_completa: MatrizCompleta | None = None
    carga: ConferenciaDaCarga | None = None
    cenarios: list[CenarioDeSeguranca]

    @classmethod
    def dos_cenarios(
        cls,
        executada_em: datetime,
        cenarios: list[CenarioDeSeguranca],
        matriz_completa: MatrizCompleta | None = None,
        carga: ConferenciaDaCarga | None = None,
    ) -> "ExecucaoDeAceite":
        """A execução com o resumo contado dos cenários."""
        resumo = Contagem(
            executados=len(cenarios),
            **Contagem.contar((c.obtido, c.divergencia) for c in cenarios),
        )
        return cls(
            executada_em=executada_em,
            resumo=resumo,
            matriz_completa=matriz_completa,
            carga=carga,
            cenarios=cenarios,
        )


def ler_ultima_execucao(pasta: Path) -> ExecucaoDeAceite | None:
    """A última execução gravada na pasta; `None` se ainda não houve nenhuma."""
    arquivo = pasta / ARQUIVO_DA_ULTIMA_EXECUCAO
    try:
        conteudo = arquivo.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    return ExecucaoDeAceite.model_validate_json(conteudo)


def gravar_execucao(execucao: ExecucaoDeAceite, pasta: Path) -> Path:
    """Grava a execução no lugar da anterior, de uma vez: quem lê nunca vê o arquivo pela
    metade."""
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / ARQUIVO_DA_ULTIMA_EXECUCAO
    descritor, temporario = tempfile.mkstemp(dir=pasta, suffix=".tmp")
    with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
        arquivo.write(execucao.model_dump_json(indent=2))
    os.replace(temporario, destino)
    return destino
