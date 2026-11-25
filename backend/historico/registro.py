"""A gravação e a leitura das conversas no banco do histórico.

Toda consulta filtra pelo `sub` e pelo perfil do usuário autenticado: a conversa de outro usuário,
ou do mesmo usuário com outro perfil, é tratada como uma que não existe (RF-18).
"""

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import datetime
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
# A lista traz só as conversas mais recentes, para não ficar pesada.
CONVERSAS_NA_LISTA = 50


class Situacao(StrEnum):
    """Como a resposta terminou. A carga deriva daqui os valores aceitos pela tabela."""

    CONCLUIDA = "concluida"
    ERRO = "erro"
    INTERROMPIDA = "interrompida"


# Como terminou uma chamada do rastreio. Negada, inexistente, com parâmetro inválido, barrada pelo
# limite ou com falha: o rastreio não distingue o motivo, que fica só no log e na auditoria.
Desfecho = Literal["concluida", "nao_concluida"]


@dataclass(frozen=True)
class ChamadaRastreada:
    """Uma chamada do rastreio da resposta: a ferramenta pedida, o desfecho e a duração.

    Sem parâmetros nem texto de erro: o rastreio é o que o usuário vê (FE §8).
    """

    ferramenta: str
    desfecho: Desfecho
    milissegundos: int


@dataclass(frozen=True)
class FimDaResposta:
    """Como a resposta terminou: a situação, o aviso ou o erro e as chamadas terminadas até ali."""

    situacao: Situacao
    aviso: str | None = None
    erro: str | None = None
    rastreio: tuple[ChamadaRastreada, ...] = ()


@dataclass(frozen=True)
class ItemGravado:
    """Uma pergunta ou resposta gravada, com o identificador da pergunta (a pergunta gravada
    antes de ele ser gravado com ela não o tem). Só a resposta tem o fim."""

    autor: Literal["usuario", "assistente"]
    texto: str
    id_da_pergunta: uuid.UUID | None = None
    fim: FimDaResposta | None = None


@dataclass(frozen=True)
class ConversaGravada:
    """Uma conversa como está no histórico, com os itens em ordem de gravação."""

    id: uuid.UUID
    titulo: str
    itens: tuple[ItemGravado, ...]


@dataclass(frozen=True)
class ResumoDaConversa:
    """Uma conversa como aparece na lista: sem os itens."""

    id: uuid.UUID
    titulo: str
    ultima_atividade: datetime


@dataclass(frozen=True)
class RespostaParaGravar:
    """A resposta ao fim do fluxo: a pergunta que ela responde, o texto emitido até ali e como
    terminou."""

    id_da_pergunta: uuid.UUID
    texto: str
    fim: FimDaResposta


class HistoricoIndisponivel(Exception):
    """O histórico não respondeu. O motivo é só para o log."""


class ConversaInexistente(Exception):
    """A conversa não existe, ou não é de quem pede: as duas dão o mesmo resultado."""


class Historico(Protocol):
    """Onde a API grava e lê as conversas. Toda operação recebe o usuário autenticado."""

    def criar_conversa(
        self, usuario: UsuarioAutenticado, primeira_pergunta: str, id_da_pergunta: uuid.UUID
    ) -> uuid.UUID:
        """Cria a conversa já com a primeira pergunta, e o começo dela como título. As duas
        coisas juntas: nenhuma conversa fica vazia."""

    def gravar_pergunta(
        self,
        usuario: UsuarioAutenticado,
        id_da_conversa: uuid.UUID,
        texto: str,
        id_da_pergunta: uuid.UUID,
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

    def listar_conversas(self, usuario: UsuarioAutenticado) -> tuple[ResumoDaConversa, ...]:
        """As conversas do usuário, da última atividade mais recente para a mais antiga, até o
        teto da lista."""

    def apagar_conversa(self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID) -> None:
        """Apaga a conversa e os itens dela, de modo definitivo, ou levanta ConversaInexistente."""


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
LISTA = """
select id, titulo, ultima_atividade from historico.conversa
where id_do_usuario = %(usuario)s and perfil = %(perfil)s
order by ultima_atividade desc, id
limit %(teto)s
"""
# Os itens vão junto, pela chave estrangeira com `on delete cascade`.
EXCLUSAO = f"delete from historico.conversa where {DO_USUARIO}"


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

    def criar_conversa(
        self, usuario: UsuarioAutenticado, primeira_pergunta: str, id_da_pergunta: uuid.UUID
    ) -> uuid.UUID:
        identificador = uuid.uuid4()
        parametros = _parametros(usuario, identificador)
        pergunta = ItemGravado("usuario", primeira_pergunta, id_da_pergunta)
        with self._conexao() as conexao, conexao.transaction():
            conexao.execute(
                CRIACAO, {**parametros, "titulo": primeira_pergunta[:TAMANHO_DO_TITULO]}
            )
            _inserir_item(conexao, parametros, pergunta)
        return identificador

    def gravar_pergunta(
        self,
        usuario: UsuarioAutenticado,
        id_da_conversa: uuid.UUID,
        texto: str,
        id_da_pergunta: uuid.UUID,
    ) -> None:
        self._gravar_item(usuario, id_da_conversa, ItemGravado("usuario", texto, id_da_pergunta))

    def gravar_resposta(
        self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID, resposta: RespostaParaGravar
    ) -> None:
        item = ItemGravado("assistente", resposta.texto, resposta.id_da_pergunta, resposta.fim)
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
                    id_da_pergunta,
                    # Só a resposta tem situação: a tabela garante.
                    FimDaResposta(
                        Situacao(situacao),
                        aviso,
                        erro,
                        tuple(ChamadaRastreada(**chamada) for chamada in rastreio),
                    )
                    if situacao
                    else None,
                )
                for autor, texto, situacao, aviso, erro, id_da_pergunta, rastreio in itens
            ),
        )

    def listar_conversas(self, usuario: UsuarioAutenticado) -> tuple[ResumoDaConversa, ...]:
        parametros = {"usuario": usuario.id, "perfil": usuario.perfil.value}
        with self._conexao() as conexao:
            linhas = conexao.execute(LISTA, {**parametros, "teto": CONVERSAS_NA_LISTA}).fetchall()
        return tuple(ResumoDaConversa(*linha) for linha in linhas)

    def apagar_conversa(self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID) -> None:
        with self._conexao() as conexao:
            if conexao.execute(EXCLUSAO, _parametros(usuario, id_da_conversa)).rowcount == 0:
                raise ConversaInexistente()

    def _gravar_item(
        self, usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID, item: ItemGravado
    ) -> None:
        parametros = _parametros(usuario, id_da_conversa)
        # A atividade e o item juntos: o item só entra se a conversa é do usuário.
        with self._conexao() as conexao, conexao.transaction():
            if conexao.execute(ATIVIDADE, parametros).rowcount == 0:
                raise ConversaInexistente()
            _inserir_item(conexao, parametros, item)

    @contextmanager
    def _conexao(self) -> Iterator[psycopg.Connection]:
        """Uma conexão do pool em que toda falha do banco sai como HistoricoIndisponivel."""
        try:
            with self._pool.connection() as conexao:
                yield conexao
        except (psycopg.Error, PoolTimeout) as erro:
            # Só o tipo e o código do erro: o detalhe do Postgres pode citar a linha recusada, e
            # com ela o texto da pergunta, que nunca vai para o log.
            codigo = getattr(erro, "sqlstate", None)
            raise HistoricoIndisponivel(
                f"{type(erro).__name__} ({codigo})" if codigo else type(erro).__name__
            ) from erro

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


def _inserir_item(conexao: psycopg.Connection, parametros: dict, item: ItemGravado) -> None:
    fim = item.fim
    conexao.execute(
        GRAVACAO_DO_ITEM,
        {
            **parametros,
            "autor": item.autor,
            "texto": item.texto,
            "situacao": fim.situacao.value if fim else None,
            "aviso": fim.aviso if fim else None,
            "erro": fim.erro if fim else None,
            "pergunta": item.id_da_pergunta,
            "rastreio": Jsonb([asdict(chamada) for chamada in fim.rastreio] if fim else []),
        },
    )


def _parametros(usuario: UsuarioAutenticado, id_da_conversa: uuid.UUID) -> dict:
    return {"conversa": id_da_conversa, "usuario": usuario.id, "perfil": usuario.perfil.value}


def historico_do_ambiente() -> HistoricoNoBanco:
    """O histórico no Postgres do ambiente, o mesmo servidor do banco carregado."""
    banco = replace(banco_do_ambiente(), nome=BANCO)
    return HistoricoNoBanco(banco, Credencial(PAPEL, os.environ["SENHA_DO_PAPEL_HISTORICO"]))
