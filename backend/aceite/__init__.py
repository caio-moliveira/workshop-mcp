"""A execução de aceite: a forma do resultado gravado, que a API lê para o painel de segurança.

Só a forma, a leitura e a gravação do arquivo e a pasta pela configuração moram aqui, sem
dependência dos testes: a API os importa. Os cenários e quem os executa ficam em
`tests/execucao_de_aceite.py`.
"""

from aceite.ambiente import PASTA_PADRAO_DA_EXECUCAO_DE_ACEITE, execucao_de_aceite_do_ambiente
from aceite.resultado import (
    ARQUIVO_DA_ULTIMA_EXECUCAO,
    CAMADAS_DE_DEFESA,
    GRUPOS,
    Alvo,
    CamadaDeDefesa,
    CenarioDeSeguranca,
    ConferenciaDaCarga,
    Contagem,
    ContagemDeDesfechos,
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
    "PASTA_PADRAO_DA_EXECUCAO_DE_ACEITE",
    "CAMADAS_DE_DEFESA",
    "GRUPOS",
    "Alvo",
    "CamadaDeDefesa",
    "CenarioDeSeguranca",
    "ConferenciaDaCarga",
    "Contagem",
    "ContagemDeDesfechos",
    "Desfecho",
    "ExecucaoDeAceite",
    "Grupo",
    "LinhaDaAuditoria",
    "MatrizCompleta",
    "Quem",
    "Resposta",
    "execucao_de_aceite_do_ambiente",
    "gravar_execucao",
    "ler_ultima_execucao",
]
