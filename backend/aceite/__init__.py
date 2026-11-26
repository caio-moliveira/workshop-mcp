"""A execução de aceite: a forma do resultado gravado, que a API lê para o painel de segurança.

Só a forma e a leitura e gravação do arquivo moram aqui, sem dependência dos testes: a API a
importa. Os cenários e quem os executa ficam em `tests/execucao_de_aceite.py`.
"""

from aceite.resultado import (
    ARQUIVO_DA_ULTIMA_EXECUCAO,
    CAMADAS_DE_DEFESA,
    GRUPOS,
    Alvo,
    CamadaDeDefesa,
    Cenario,
    ConferenciaDaCarga,
    Contagem,
    Desfecho,
    ExecucaoDeAceite,
    Grupo,
    LinhaDaAuditoria,
    MatrizCompleta,
    Quem,
    Resposta,
    gravar_execucao,
    ler_ultima_execucao,
)

__all__ = [
    "ARQUIVO_DA_ULTIMA_EXECUCAO",
    "CAMADAS_DE_DEFESA",
    "GRUPOS",
    "Alvo",
    "CamadaDeDefesa",
    "Cenario",
    "ConferenciaDaCarga",
    "Contagem",
    "Desfecho",
    "ExecucaoDeAceite",
    "Grupo",
    "LinhaDaAuditoria",
    "MatrizCompleta",
    "Quem",
    "Resposta",
    "gravar_execucao",
    "ler_ultima_execucao",
]
