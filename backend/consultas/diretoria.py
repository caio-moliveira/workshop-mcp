"""As consultas da Diretoria. Leem só a camada de leitura da Diretoria, já agregada (ADR 0011).

Cada view da camada traz as linhas dos quatro períodos, com o período como coluna: a consulta só
filtra o período pedido e não agrega. As respostas trazem números crus e datas ISO; a formatação é
do frontend.
"""

from consultas.lead import Canal
from consultas.periodo import Periodo

# As dimensões fechadas da camada: cada coluna de texto de uma view é uma delas, e os valores que
# ela traz são exatamente os da enumeração.
DIMENSOES: dict[str, tuple[str, ...]] = {
    "periodo": tuple(periodo.value for periodo in Periodo),
    "canal": tuple(canal.value for canal in Canal),
}
