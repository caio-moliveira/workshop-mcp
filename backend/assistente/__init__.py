"""O assistente da aplicação: responde perguntas com as ferramentas do servidor MCP.

Chama o servidor MCP com o token do usuário que perguntou, nunca com credencial própria.
"""

from assistente.limites import Limites, limites_do_ambiente
from assistente.modelo import MODELO_PADRAO, modelo_do_ambiente
from assistente.resposta import Assistente, Evento

__all__ = [
    "MODELO_PADRAO",
    "Assistente",
    "Evento",
    "Limites",
    "limites_do_ambiente",
    "modelo_do_ambiente",
]
