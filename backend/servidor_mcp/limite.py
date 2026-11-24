"""O limite de frequência: quantas chamadas cada usuário pode fazer numa janela deslizante (RS-11).

Em memória: o servidor MCP é uma instância só, e o contador zera quando o processo reinicia.
"""

import os
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable, Mapping

# O padrão, quando o ambiente não diz: o único lugar do código com esses números.
CHAMADAS_PADRAO = 30
JANELA_PADRAO_EM_SEGUNDOS = 60.0


class LimiteDeFrequencia:
    """Conta as chamadas de cada usuário (pelo identificador do token) nos últimos segundos.

    O `relogio` dá o tempo em segundos; o teste passa um falso para avançar sem esperar.
    """

    def __init__(
        self,
        chamadas: int,
        janela_em_segundos: float,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self._chamadas = chamadas
        self._janela = janela_em_segundos
        self._relogio = relogio
        self._horarios: dict[str, deque[float]] = defaultdict(deque)
        # As chamadas de um mesmo usuário podem chegar ao mesmo tempo.
        self._trava = threading.Lock()

    def admitir(self, id_do_usuario: str) -> bool:
        """Se o usuário ainda cabe no limite. Só a chamada admitida conta: a barrada, não."""
        agora = self._relogio()
        with self._trava:
            horarios = self._horarios[id_do_usuario]
            while horarios and horarios[0] <= agora - self._janela:
                horarios.popleft()
            if len(horarios) >= self._chamadas:
                return False
            horarios.append(agora)
            return True


def limite_do_ambiente(
    ambiente: Mapping[str, str] = os.environ, relogio: Callable[[], float] = time.monotonic
) -> LimiteDeFrequencia:
    """O limite das variáveis de ambiente; sem elas, o padrão."""
    return LimiteDeFrequencia(
        chamadas=int(ambiente.get("LIMITE_DE_CHAMADAS_POR_USUARIO", CHAMADAS_PADRAO)),
        janela_em_segundos=float(
            ambiente.get("JANELA_DO_LIMITE_EM_SEGUNDOS", JANELA_PADRAO_EM_SEGUNDOS)
        ),
        relogio=relogio,
    )
