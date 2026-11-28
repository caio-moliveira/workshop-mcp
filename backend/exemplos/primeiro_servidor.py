"""O menor servidor MCP que faz algo útil: uma ferramenta, sem login.

Usado no workshop, na parte de fundamentos, para mostrar o protocolo antes de qualquer camada de
segurança. Não faz parte da aplicação. Para rodar, dentro de `backend/`:

    uv run python exemplos/primeiro_servidor.py

Ele sobe em http://localhost:8002/mcp. Qualquer um que alcance o endereço chama a ferramenta:
é exatamente o que o resto do projeto resolve.
"""

from typing import Literal

from fastmcp import FastMCP

servidor = FastMCP("primeiro-servidor")

# Valores fixos, só de exemplo: o servidor de verdade consulta o banco.
PEDIDOS_POR_PERIODO = {"30d": 1400, "90d": 4200, "12m": 16795}


@servidor.tool
def pedidos_realizados(periodo: Literal["30d", "90d", "12m"] = "12m") -> dict:
    """Quantos pedidos o marketplace recebeu no período. Use para perguntas sobre volume de
    vendas."""
    return {"periodo": periodo, "pedidos": PEDIDOS_POR_PERIODO[periodo]}


if __name__ == "__main__":
    # Sem sessão, como o servidor do projeto: cada requisição se basta.
    servidor.run(transport="http", host="127.0.0.1", port=8002, stateless_http=True)
