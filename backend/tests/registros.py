"""Auxiliares das matrizes de isolamento: quem é dono de cada rota e de cada ferramenta.

Tudo é lido dos registros (`ROTAS_DE_DADOS` da API e `FERRAMENTAS` do servidor MCP): o dono é o
perfil da consulta servida. Uma rota ou ferramenta nova entra nas matrizes sem mudar os testes.
"""

from acesso import Perfil
from api.aplicacao import ROTAS_DE_DADOS
from servidor_mcp.ferramentas import FERRAMENTAS

DONO_DA_ROTA = {rota: consulta.perfil for rota, consulta in ROTAS_DE_DADOS.items()}
DONO_DA_FERRAMENTA = {nome: ferramenta.consulta.perfil for nome, ferramenta in FERRAMENTAS.items()}


def ferramentas_de(perfil: Perfil) -> list[str]:
    """Os nomes das ferramentas do perfil, em ordem alfabética. Vazio para quem não tem nenhuma."""
    return sorted(nome for nome, dono in DONO_DA_FERRAMENTA.items() if dono is perfil)


def _primeiro_valor_valido(esquema: dict) -> str | int:
    """O primeiro valor que o esquema JSON do parâmetro aceita: da enumeração ou da faixa."""
    if "enum" in esquema:
        return esquema["enum"][0]
    return esquema["minimum"]


def argumentos_minimos(ferramenta: str) -> dict[str, str | int]:
    """Os argumentos obrigatórios da ferramenta, cada um com o primeiro valor que ele aceita."""
    return {
        parametro.nome: _primeiro_valor_valido(parametro.esquema())
        for parametro in FERRAMENTAS[ferramenta].parametros
        if parametro.obrigatorio
    }
