"""O assistente da aplicação: responde perguntas com as ferramentas do servidor MCP.

Chama o servidor MCP com o token do usuário que perguntou, nunca com credencial própria.
"""

from assistente.agente import Assistente, Evento
from assistente.modelo import MODELO_PADRAO, modelo_do_ambiente

__all__ = ["MODELO_PADRAO", "Assistente", "Evento", "modelo_do_ambiente"]
