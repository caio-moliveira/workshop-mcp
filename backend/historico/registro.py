"""A gravação e a leitura das conversas no banco do histórico.

Toda consulta filtra pelo `sub` e pelo perfil do usuário autenticado: a conversa de outro usuário,
ou do mesmo usuário com outro perfil, é tratada como uma que não existe (RF-18).
"""

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from types import TracebackType
from typing import Literal, Protocol

import psycopg
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout

from acesso import UsuarioAutenticado
from consultas import BancoDeDados, Credencial, banco_do_ambiente

# O banco próprio do histórico e o papel que lê e grava nele. A carga cria os dois com estes nomes.
BANCO = "historico"
PAPEL = "historico"
# Quanto uma pergunta espera pelo histórico antes de desistir.
ESPERA_POR_CONEXAO_EM_SEGUNDOS = 5
CONEXOES = 4
# O título da conversa é o começo da primeira pergunta, cortado aqui.
TAMANHO_DO_TITULO = 80


class Situacao(StrEnum):
    """Como a resposta terminou. A carga deriva daqui os valores aceitos pela tabela."""

    CONCLUIDA = "concluida"
    ERRO = "erro"
    INTERROMPIDA = "interrompida"


@dataclass(frozen=True)
class ChamadaRastreada:
    """Uma chamada do rastreio da resposta: a ferramenta pedida, o desfecho e a duração.

    Sem parâmetros nem texto de erro: o rastreio é o que o usuário vê (FE §8).
    """

    ferramenta: str
    desfecho: Literal["concluida", "nao_concluida"]
    milissegundos: int


@dataclass(frozen=True)
class ItemGravado:
    """Uma pergunta ou resposta gravada. Só a resposta tem situação, aviso, erro, pergunta e
    rastreio."""

    autor: Literal["usuario", "assistente"]
    texto: str
    situacao: Situacao | None = None
    aviso: str | None = None
    erro: str | None = None
    id_da_pergunta: uuid.UUID | None = None
    rastreio: tuple[ChamadaRastreada, ...] = ()


@dataclass(frozen=True)
class ConversaGravada:
    """Uma conversa como está no histórico, com os itens em ordem de gravação."""

    id: uuid.UUID
    titulo: str
    itens: tuple[ItemGravado, ...]


@dataclass(frozen=True)
class RespostaParaGravar:
    """A resposta ao fim do fluxo: o texto emitido até ali, a situação, o aviso ou o erro e as
    chamadas terminadas até ali."""

    id_da_pergunta: uuid.UUID
    texto: str
    situacao: Situacao
    aviso: str | None = None
    erro: str | None = None
    rastreio: tuple[ChamadaRastreada, ...] = ()


class HistoricoIndisponivel(Exception):
    """O histórico não respondeu. O motivo é só para o log."""


class ConversaInexistente(Exception):
    """A conversa não existe, ou não é de quem pede: as duas dão o mesmo resultado."""


class Historico(Protocol):
    """Onde a API grava e lê as conversas. Toda operação recebe o usuário autenticado."""

    def criar_conversa(self, usuario: UsuarioAutenticado, primeira_pergunta: str) -> uuid.UUID:
        """Cria uma conversa vazia, com o começo da primeira pergunta como título."""

    def gravar_pergunta(
        self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID, texto: str
    ) -> None:
        """Acrescenta a pergunta à conversa, ou levanta ConversaInexistente."""

    def gravar_resposta(
        self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID, resposta: RespostaParaGravar
    ) -> None:
        """Acrescenta a resposta à conversa, ou levanta ConversaInexistente."""

    def ler_conversa(
        self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID
    ) -> ConversaGravada:
        """A conversa com os itens em ordem, ou ConversaInexistente."""


# A conversa só é tocada quando é do usuário: o mesmo `sub` e o mesmo perfil.
DO_USUARIO = "id = %(conversa)s and id_do_usuario = %(usuario)s and perfil = %(perfil)s"

CRIACAO = """
insert into historico.conversa (id, id_do_usuario, perfil, titulo, ultima_atividade)
values (%(conversa)s, %(usuario)s, %(perfil)s, %(titulo)s, now())
"""
ATIVIDADE = f"update historico.conversa set ultima_atividade = now() where {DO_USUARIO}"
GRAVACAO_DO_ITEM = """
insert into historico.item (
    id_da_conversa, autor, texto, horario, situacao, aviso, erro, id_da_pergunta, rastreio
) values (
    %(conversa)s, %(autor)s, %(texto)s, now(), %(situacao)s, %(aviso)s, %(erro)s,
    %(pergunta)s, %(rastreio)s
)
"""
LEITURA_DA_CONVERSA = f"select titulo from historico.conversa where {DO_USUARIO}"
LEITURA_DOS_ITENS = """
select autor, texto, situacao, aviso, erro, id_da_pergunta, rastreio from historico.item
where id_da_conversa = %(conversa)s order by ordem
"""


class HistoricoNoBanco:
    """O histórico no banco próprio, com um pool de conexões do papel `historico`.

    Feche ao terminar (`with` ou `fechar()`).
    """

    def __init__(self, banco: BancoDeDados, credencial: Credencial) -> None:
        self._pool = ConnectionPool(
            kwargs={
                "host": banco.host,
                "port": banco.porta,
                "dbname": banco.nome,
                "user": credencial.papel,
                "password": credencial.senha,
                "connect_timeout": ESPERA_POR_CONEXAO_EM_SEGUNDOS,
                "autocommit": True,
            },
            # Sem conexão aberta na subida: a API sobe mesmo com o histórico fora, e é a pergunta
            # que é recusada.
            min_size=0,
            max_size=CONEXOES,
            timeout=ESPERA_POR_CONEXAO_EM_SEGUNDOS,
            check=ConnectionPool.check_connection,
            name="historico",
            open=True,
        )

    def criar_conversa(self, usuario: UsuarioAutenticado, primeira_pergunta: str) -> uuid.UUID:
        identificador = uuid.uuid4()
        with self._conexao() as conexao:
            conexao.execute(
                CRIACAO,
                {
                    **_parametros(usuario, identificador),
                    "titulo": primeira_pergunta[:TAMANHO_DO_TITULO],
                },
            )
        return identificador

    def gravar_pergunta(
        self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID, texto: str
    ) -> None:
        self._gravar_item(usuario, id_da_conversa, ItemGravado("usuario", texto))

    def gravar_resposta(
        self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID, resposta: RespostaParaGravar
    ) -> None:
        item = ItemGravado(
            "assistente",
            resposta.texto,
            situacao=resposta.situacao,
            aviso=resposta.aviso,
            erro=resposta.erro,
            id_da_pergunta=resposta.id_da_pergunta,
            rastreio=resposta.rastreio,
        )
        self._gravar_item(usuario, id_da_conversa, item)

    def ler_conversa(
        self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID
    ) -> ConversaGravada:
        parametros = _parametros(usuario, id_da_conversa)
        with self._conexao() as conexao:
            linha = conexao.execute(LEITURA_DA_CONVERSA, parametros).fetchone()
            if linha is None:
                raise ConversaInexistente()
            itens = conexao.execute(LEITURA_DOS_ITENS, parametros).fetchall()
        return ConversaGravada(
            id=id_da_conversa,
            titulo=linha[0],
            itens=tuple(
                ItemGravado(
                    autor,
                    texto,
                    situacao=Situacao(situacao) if situacao else None,
                    aviso=aviso,
                    erro=erro,
                    id_da_pergunta=id_da_pergunta,
                    rastreio=tuple(ChamadaRastreada(**chamada) for chamada in rastreio),
                )
                for autor, texto, situacao, aviso, erro, id_da_pergunta, rastreio in itens
            ),
        )

    def _gravar_item(
        self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID, item: ItemGravado
    ) -> None:
        parametros = _parametros(usuario, id_da_conversa)
        # A atividade e o item juntos: o item só entra se a conversa é do usuário.
        with self._conexao() as conexao, conexao.transaction():
            if conexao.execute(ATIVIDADE, parametros).rowcount == 0:
                raise ConversaInexistente()
            conexao.execute(
                GRAVACAO_DO_ITEM,
                {
                    **parametros,
                    "autor": item.autor,
                    "texto": item.texto,
                    "situacao": item.situacao.value if item.situacao else None,
                    "aviso": item.aviso,
                    "erro": item.erro,
                    "pergunta": item.id_da_pergunta,
                    "rastreio": Jsonb([asdict(chamada) for chamada in item.rastreio]),
                },
            )

    @contextmanager
    def _conexao(self) -> Iterator[psycopg.Connection]:
        """Uma conexão do pool em que toda falha do banco sai como HistoricoIndisponivel."""
        try:
            with self._pool.connection() as conexao:
                yield conexao
        except (psycopg.Error, PoolTimeout) as erro:
            raise HistoricoIndisponivel(str(erro)) from erro

    def fechar(self) -> None:
        self._pool.close()

    def __enter__(self) -> "HistoricoNoBanco":
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        erro: BaseException | None,
        rastro: TracebackType | None,
    ) -> None:
        self.fechar()


def _parametros(usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID) -> dict:
    return {"conversa": id_da_conversa, "usuario": usuario.id, "perfil": usuario.perfil.value}


def historico_do_ambiente() -> HistoricoNoBanco:
    """O histórico no Postgres do ambiente, o mesmo servidor do banco carregado."""
    banco = replace(banco_do_ambiente(), nome=BANCO)
    return HistoricoNoBanco(banco, Credencial(PAPEL, os.environ["SENHA_DO_PAPEL_HISTORICO"]))
