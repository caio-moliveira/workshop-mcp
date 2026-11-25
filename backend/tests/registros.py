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


def argumentos_minimos(ferramenta: str) -> dict[str, str]:
    """Os argumentos obrigatórios da ferramenta, cada um com o primeiro valor da enumeração."""
    return {
        parametro.nome: next(iter(parametro.enumeracao)).value
        for parametro in FERRAMENTAS[ferramenta].parametros
        if parametro.padrao is None
    }
