"""O registro de uma consulta: uma função de leitura e o único perfil que pode executá-la."""

from collections.abc import Callable
from dataclasses import dataclass

from acesso import Perfil


@dataclass(frozen=True)
class Consulta[R]:
    """Uma leitura da camada de um perfil. Sem perfil declarado, não existe consulta (RS-05).

    `ler` recebe a conexão aberta com o papel do perfil e os parâmetros já validados.
    """

    nome: str
    perfil: Perfil
    ler: Callable[..., R]

    def __post_init__(self) -> None:
        if not isinstance(self.perfil, Perfil):
            raise TypeError(f"a consulta {self.nome} precisa declarar um Perfil")


def consulta[R](perfil: Perfil) -> Callable[[Callable[..., R]], Consulta[R]]:
    """Registra a função decorada como consulta do perfil dado.

    @consulta(Perfil.VENDAS)
    def indicadores(conexao, periodo): ...
    """

    def registrar(ler: Callable[..., R]) -> Consulta[R]:
        return Consulta(nome=ler.__name__, perfil=perfil, ler=ler)

    return registrar
