"""O servidor MCP: as consultas do pulso. como ferramentas para agentes de IA.

O pacote não se chama `mcp` porque esse é o nome do pacote do SDK que o FastMCP importa.
"""

from servidor_mcp.limite import LimiteDeFrequencia, limite_do_ambiente
from servidor_mcp.servidor import criar_aplicacao

__all__ = ["LimiteDeFrequencia", "criar_aplicacao", "limite_do_ambiente"]
