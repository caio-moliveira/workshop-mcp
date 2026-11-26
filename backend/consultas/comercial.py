"""As consultas do Comercial. Leem só a camada de leitura do Comercial (ADR 0002).

Cada número usa a data do próprio fato (glossário): leads, leads em negociação e principal canal,
a data de criação; novos lojistas e dias até fechar, a data de fechamento. As respostas trazem
números crus e datas ISO; a formatação é do frontend.
"""

from dataclasses import dataclass
from datetime import date

import psycopg

from acesso import Perfil
from consultas.periodo import DatasDoPeriodo, Periodo, inicio_dos_dados, terminado_em
from consultas.registro import consulta

# Lead em negociação: ainda não fechou nem foi perdido (glossário).
ETAPAS_EM_NEGOCIACAO = ["Novo", "Contatado", "Qualificado", "Proposta"]


@dataclass(frozen=True)
class _Resumo:
    leads: int
    leads_em_negociacao: int
    novos_lojistas: int
    dias_ate_fechar: float | None

    @property
    def conversao(self) -> float | None:
        """Novos lojistas do período por leads criados no período: uma razão, não uma coorte."""
        return self.novos_lojistas / self.leads if self.leads else None


def _data_de_referencia(conexao: psycopg.Connection) -> date:
    return conexao.execute("select data_referencia from comercial.referencia").fetchone()[0]


def _datas_do(periodo: Periodo, conexao: psycopg.Connection) -> DatasDoPeriodo:
    """As datas do período que termina na data de referência dos dados."""
    return terminado_em(periodo, _data_de_referencia(conexao))


def _parametros(datas: DatasDoPeriodo) -> dict:
    return {"inicio": datas.inicio, "fim": datas.fim, "em_negociacao": ETAPAS_EM_NEGOCIACAO}


def _resumo(conexao: psycopg.Connection, datas: DatasDoPeriodo) -> _Resumo:
    linha = conexao.execute(
        """
        with criados as (
            select etapa from comercial.lead
            where data_criacao between %(inicio)s and %(fim)s
        ),
        fechados as (
            select data_fechamento - data_criacao as dias from comercial.lead
            where data_fechamento between %(inicio)s and %(fim)s
        )
        select
            (select count(*) from criados),
            (select count(*) from criados where etapa = any(%(em_negociacao)s)),
            (select count(*) from fechados),
            (select avg(dias)::float from fechados)
        """,
        _parametros(datas),
    ).fetchone()
    return _Resumo(*linha)


def _principal_canal(conexao: psycopg.Connection, datas: DatasDoPeriodo) -> tuple[str, int] | None:
    """O canal com mais leads criados no período e quantos são, ou `None` sem lead no período.

    No empate, vence o canal com mais novos lojistas no período; persistindo, a ordem alfabética.
    """
    return conexao.execute(
        """
        select canal, count(*) filter (where data_criacao between %(inicio)s and %(fim)s) as leads
        from comercial.lead
        group by canal
        having count(*) filter (where data_criacao between %(inicio)s and %(fim)s) > 0
        order by
            leads desc,
            count(*) filter (where data_fechamento between %(inicio)s and %(fim)s) desc,
            canal
        limit 1
        """,
        _parametros(datas),
    ).fetchone()


@consulta(Perfil.COMERCIAL)
def indicadores(conexao: psycopg.Connection, periodo: Periodo) -> dict:
    """Do período: leads criados, os em negociação entre eles, novos lojistas, dias médios até
    fechar, conversão, principal canal e a parcela dele nos leads. Do anterior: leads, novos
    lojistas e conversão.

    O anterior tem o mesmo tamanho e termina na véspera do início; é `None` quando começaria antes
    do início dos dados, como em Vendas. A conversão, o principal canal e a parcela são `None` num
    período sem lead criado, e os dias até fechar, num período sem novo lojista.
    """
    atual = _datas_do(periodo, conexao)
    datas_anteriores = atual.anterior(periodo)
    agora = _resumo(conexao, atual)
    antes = (
        _resumo(conexao, datas_anteriores)
        if datas_anteriores.inicio >= inicio_dos_dados(atual.fim)
        else None
    )
    principal = _principal_canal(conexao, atual)

    def comparacao(indicador: str) -> dict:
        return {
            "atual": getattr(agora, indicador),
            "anterior": None if antes is None else getattr(antes, indicador),
        }

    return {
        "periodo": atual.como_json(),
        "leads": comparacao("leads"),
        "leads_em_negociacao": agora.leads_em_negociacao,
        "novos_lojistas": comparacao("novos_lojistas"),
        "dias_ate_fechar": agora.dias_ate_fechar,
        "conversao": comparacao("conversao"),
        "principal_canal": None if principal is None else principal[0],
        "parcela_do_principal_canal": None if principal is None else principal[1] / agora.leads,
    }
