"""Os tetos de uma pergunta ao assistente, lidos da configuração."""

import os
from dataclasses import dataclass

# A conversa reenviada pelo navegador: até tantos itens, cada um dentro do teto de caracteres.
ITENS_DA_CONVERSA = 20


@dataclass(frozen=True)
class Limites:
    """Quanto uma pergunta pode pedir: chamadas de ferramenta, caracteres e tempo."""

    # Chamadas de ferramenta por pergunta. Ao atingir, a resposta para com um aviso.
    chamadas: int = 8
    # Caracteres da pergunta e de cada item da conversa reenviada.
    caracteres: int = 2000
    # Tempo máximo da pergunta inteira, em segundos.
    segundos: float = 60

    @property
    def requisicoes_ao_modelo(self) -> int:
        """Uma requisição por chamada e a da resposta final, com folga.

        Segura também o laço de nomes de ferramenta que o servidor não listou, que não contam
        como chamadas: são recusados dentro da API, sem chegar ao servidor MCP.
        """
        return self.chamadas + 2


PADRAO = Limites()


def limites_do_ambiente() -> Limites:
    """Os tetos das variáveis de ambiente; o padrão de cada um quando a variável falta."""
    return Limites(
        chamadas=int(os.environ.get("LIMITE_DE_CHAMADAS_POR_PERGUNTA") or PADRAO.chamadas),
        caracteres=int(os.environ.get("LIMITE_DE_CARACTERES_DA_PERGUNTA") or PADRAO.caracteres),
        segundos=float(os.environ.get("TEMPO_MAXIMO_DA_PERGUNTA_EM_SEGUNDOS") or PADRAO.segundos),
    )
