"""Lado comercial: leads, com canal e etapa do funil, e os lojistas que nasceram deles."""

import random
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import date, timedelta

from faker import Faker

from carga.calendario import Calendario, dias_entre
from carga.documentos import cnpj_ficticio
from carga.geografia import CIDADES, Cidade

# Leads e fechamentos por canal. Mídia paga converte bem: o Comercial a vê como um bom canal.
LEADS_E_FECHAMENTOS_POR_CANAL: tuple[tuple[str, int, int], ...] = (
    ("Indicação", 180, 45),
    ("Orgânico", 375, 50),
    ("Mídia paga", 450, 135),
    ("Eventos", 165, 30),
    ("Prospecção ativa", 330, 40),
)
LOJISTAS_ANTES_DA_JANELA = 80
ETAPA_FECHADO = "Fechado"
ETAPA_PERDIDO = "Perdido"
ETAPAS_ABERTAS = ("Novo", "Contatado", "Qualificado", "Proposta")
DIAS_ATE_UM_LEAD_PARADO_SER_PERDIDO = 120


@dataclass(frozen=True)
class Lojista:
    id: int
    nome: str
    cnpj: str
    cidade: str
    uf: str


@dataclass(frozen=True)
class Lead:
    id: int
    nome_empresa: str
    email_contato: str
    canal: str
    etapa: str
    data_criacao: date
    data_fechamento: date | None
    lojista_id: int | None


@dataclass(frozen=True)
class Comercial:
    leads: list[Lead]
    lojistas: list[Lojista]


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def _email_ficticio(nome_empresa: str) -> str:
    dominio = re.sub(r"[^a-z0-9]+", "-", _sem_acento(nome_empresa).lower()).strip("-")
    return f"contato@{dominio}.example"


def _dia_com_crescimento(rng: random.Random, dias: list[date]) -> date:
    """Sorteia um dia, com peso que cresce ao longo do período (até o dobro no fim)."""
    pesos = [1 + i / len(dias) for i in range(len(dias))]
    return rng.choices(dias, weights=pesos)[0]


def _etapa_de_lead_nao_fechado(rng: random.Random, idade_em_dias: int) -> str:
    if idade_em_dias > DIAS_ATE_UM_LEAD_PARADO_SER_PERDIDO or rng.random() < 0.3:
        return ETAPA_PERDIDO
    mais_avancada = min(len(ETAPAS_ABERTAS) - 1, idade_em_dias // 30)
    return ETAPAS_ABERTAS[rng.randint(max(0, mais_avancada - 1), mais_avancada)]


def _novo_lead(
    nome_empresa: str,
    canal: str,
    etapa: str,
    data_criacao: date,
    data_fechamento: date | None = None,
) -> Lead:
    """Um lead ainda sem id e sem lojista: os dois são atribuídos ao final."""
    return Lead(
        id=0,
        nome_empresa=nome_empresa,
        email_contato=_email_ficticio(nome_empresa),
        canal=canal,
        etapa=etapa,
        data_criacao=data_criacao,
        data_fechamento=data_fechamento,
        lojista_id=None,
    )


def gerar_comercial(rng: random.Random, fake: Faker, calendario: Calendario) -> Comercial:
    referencia = calendario.data_referencia
    inicio_funil = calendario.inicio_do_funil
    inicio_janela = calendario.inicio_da_janela
    dias_antes_da_janela = dias_entre(
        inicio_funil + timedelta(days=20), inicio_janela - timedelta(days=1)
    )
    dias_da_janela = dias_entre(inicio_janela, referencia)
    dias_do_funil = dias_entre(inicio_funil, referencia)

    fechados: list[str] = []
    nao_fechados: list[str] = []
    for canal, leads, fechamentos in LEADS_E_FECHAMENTOS_POR_CANAL:
        fechados += [canal] * fechamentos
        nao_fechados += [canal] * (leads - fechamentos)
    rng.shuffle(fechados)
    rng.shuffle(nao_fechados)

    leads: list[Lead] = []
    cidades_dos_fechados: list[Cidade] = []
    for posicao, canal in enumerate(fechados):
        if posicao < LOJISTAS_ANTES_DA_JANELA:
            fechamento = rng.choice(dias_antes_da_janela)
        else:
            fechamento = _dia_com_crescimento(rng, dias_da_janela)
        criacao = max(inicio_funil, fechamento - timedelta(days=rng.randint(15, 75)))
        nome = fake.unique.company()
        leads.append(_novo_lead(nome, canal, ETAPA_FECHADO, criacao, data_fechamento=fechamento))
        cidades_dos_fechados.append(rng.choices(CIDADES, weights=[c.peso for c in CIDADES])[0])

    for canal in nao_fechados:
        criacao = _dia_com_crescimento(rng, dias_do_funil)
        etapa = _etapa_de_lead_nao_fechado(rng, (referencia - criacao).days)
        nome = fake.unique.company()
        leads.append(_novo_lead(nome, canal, etapa, criacao))

    # Lojistas numerados pela data de entrada; leads, pela data de criação.
    ordem_de_entrada = sorted(
        range(len(fechados)), key=lambda i: (leads[i].data_fechamento, leads[i].nome_empresa)
    )
    lojistas: list[Lojista] = []
    for lojista_id, indice in enumerate(ordem_de_entrada, start=1):
        cidade = cidades_dos_fechados[indice]
        lead = leads[indice]
        lojistas.append(
            Lojista(lojista_id, lead.nome_empresa, cnpj_ficticio(rng), cidade.nome, cidade.uf)
        )
        leads[indice] = replace(lead, lojista_id=lojista_id)

    leads.sort(key=lambda lead: (lead.data_criacao, lead.nome_empresa))
    leads = [replace(lead, id=lead_id) for lead_id, lead in enumerate(leads, start=1)]
    return Comercial(leads=leads, lojistas=lojistas)
