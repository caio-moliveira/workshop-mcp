"""O registro das ferramentas: o único lugar que diz o que o servidor MCP publica.

Cada ferramenta serve uma `Consulta`, e o perfil da ferramenta é o perfil da consulta: não há
outro lugar para declará-lo (RS-05). As descrições são escritas para o modelo de linguagem, que
escolhe a ferramenta e preenche os parâmetros a partir delas (RF-24).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from consultas import PERIODO_PADRAO, Consulta, ParametroInvalido, Periodo, vendas


@dataclass(frozen=True)
class Parametro:
    """Um parâmetro de ferramenta: sempre uma enumeração fechada do domínio (RF-23).

    A enumeração valida o valor recebido com o próprio `ler`, que levanta `ParametroInvalido`.
    Sem `padrao`, o parâmetro é obrigatório.
    """

    nome: str
    enumeracao: type[StrEnum]
    descricao: str
    padrao: StrEnum | None = None

    def esquema(self) -> dict[str, Any]:
        esquema = {
            "type": "string",
            "enum": [valor.value for valor in self.enumeracao],
            "description": self.descricao,
        }
        if self.padrao is not None:
            esquema["default"] = self.padrao.value
        return esquema

    def ler(self, argumentos: Mapping[str, Any]) -> StrEnum:
        if self.nome not in argumentos:
            if self.padrao is None:
                raise ParametroInvalido("parâmetro obrigatório ausente")
            return self.padrao
        valor = argumentos[self.nome]
        if not isinstance(valor, str):
            raise ParametroInvalido("parâmetro que não é texto")
        return self.enumeracao.ler(valor)


@dataclass(frozen=True)
class Ferramenta:
    """Uma consulta oferecida pelo servidor MCP, com o que o modelo precisa para usá-la."""

    consulta: Consulta
    titulo: str
    descricao: str
    parametros: tuple[Parametro, ...]

    def __post_init__(self) -> None:
        # Sem consulta não há perfil, e sem perfil não há ferramenta (RS-05).
        if not isinstance(self.consulta, Consulta):
            raise TypeError(f"a ferramenta {self.titulo} precisa servir uma Consulta")

    def esquema_de_entrada(self) -> dict[str, Any]:
        """O esquema JSON dos argumentos: só os parâmetros previstos, nada além deles."""
        esquema: dict[str, Any] = {
            "type": "object",
            "properties": {parametro.nome: parametro.esquema() for parametro in self.parametros},
            "additionalProperties": False,
        }
        obrigatorios = [parametro.nome for parametro in self.parametros if parametro.padrao is None]
        if obrigatorios:
            esquema["required"] = obrigatorios
        return esquema

    def ler_argumentos(self, argumentos: Mapping[str, Any]) -> dict[str, StrEnum]:
        """Os parâmetros da consulta, validados, ou `ParametroInvalido`."""
        if set(argumentos) - {parametro.nome for parametro in self.parametros}:
            raise ParametroInvalido("parâmetro fora do previsto")
        return {parametro.nome: parametro.ler(argumentos) for parametro in self.parametros}


PERIODO = Parametro(
    nome="periodo",
    enumeracao=Periodo,
    descricao=(
        "Período analisado, contado para trás a partir da data de referência dos dados (o último "
        "dia com dados, que não é o dia de hoje): '30d' = últimos 30 dias, '90d' = últimos 90 "
        "dias, '12m' = últimos 12 meses, '24m' = últimos 24 meses. Se omitido, usa '12m'."
    ),
    padrao=PERIODO_PADRAO,
)

AGRUPAMENTO_DOS_ATRASOS = Parametro(
    nome="agrupamento",
    enumeracao=vendas.AgrupamentoDeAtrasos,
    descricao=(
        "Como agrupar os pedidos entregues para ver onde o atraso se concentra: 'rota' = por "
        "trajeto do pedido, do estado (UF) do lojista ao estado (UF) do cliente, por exemplo "
        "'SP → BA'; 'lojista' = pela empresa que vendeu, identificada pelo nome. Obrigatório. "
        "Para investigar a causa dos atrasos, chame uma vez com cada valor."
    ),
)

# Cada ferramenta e a consulta que ela serve. O nome começa pelo perfil (ADR 0005). Uma
# ferramenta fora deste registro não é publicada.
FERRAMENTAS: dict[str, Ferramenta] = {
    "vendas_indicadores": Ferramenta(
        consulta=vendas.indicadores,
        titulo="Indicadores de Vendas",
        descricao=(
            "Indicadores gerais de Vendas do marketplace em um período: pedidos realizados, "
            "receita, taxa de atraso e taxa de aprovação. Use para saber como as vendas estão "
            "indo e se melhoraram ou pioraram: cada indicador traz o valor do período ('atual') "
            "e o do período imediatamente anterior, de mesmo tamanho ('anterior', que vem nulo "
            "quando não há dados anteriores para comparar). 'periodo' traz as datas de início "
            "e fim usadas, em formato ISO. A receita é a soma dos pagamentos aprovados, em "
            "reais. A taxa de aprovação é a fração (de 0 a 1) dos pedidos com pagamento "
            "aprovado. A taxa de atraso é a fração (de 0 a 1) dos pedidos entregues que "
            "chegaram depois da data prometida, e 'atrasos' é a quantidade deles no período; "
            "pedidos ainda em trânsito com prazo vencido não contam como atraso."
        ),
        parametros=(PERIODO,),
    ),
    "vendas_atrasos": Ferramenta(
        consulta=vendas.atrasos,
        titulo="Atrasos por rota ou lojista",
        descricao=(
            "Onde o atraso de entrega se concentra em um período: lista as rotas ou os lojistas "
            "com mais pedidos entregues depois da data prometida. Use para responder o que está "
            "causando os atrasos, quais rotas ou lojistas atrasam mais e se o atraso é "
            "espalhado ou concentrado em poucos; para a taxa de atraso geral e sua comparação "
            "com o período anterior, use vendas_indicadores. Só entram pedidos já entregues, no "
            "prazo ou com atraso: pedidos ainda em trânsito, inclusive os de prazo vencido, não "
            "contam como entregues nem como atraso. Cada item de 'grupos' traz 'grupo' (a rota, "
            "como 'SP → BA', ou o nome do lojista), 'entregues' (pedidos entregues do grupo), "
            "'atrasos' (quantos deles chegaram com atraso), 'taxa_de_atraso' (atrasos do grupo "
            "÷ entregues do próprio grupo, de 0 a 1: o quanto aquele grupo atrasa) e "
            "'participacao' (atrasos do grupo ÷ todos os atrasos do período, de 0 a 1: o "
            "quanto do problema vem dele). As duas medidas dizem coisas diferentes: um grupo "
            "pequeno pode ter taxa de atraso alta e participação baixa, e um grupo grande o "
            "contrário. Os grupos vêm ordenados por 'atrasos', do maior para o menor, e a "
            "lista traz no máximo os 10 primeiros com ao menos um atraso: 'grupos_com_atraso' "
            "diz quantos grupos têm atraso ao todo e 'lista_cortada' é verdadeiro quando há "
            "mais grupos do que os listados, caso em que as participações listadas somam "
            "menos que 1. 'total' traz os pedidos entregues, os atrasos e a taxa de atraso do "
            "período inteiro (nula se nada foi entregue), incluindo os grupos fora da lista. "
            "'periodo' traz as datas de início e fim usadas, em formato ISO, e 'agrupamento' "
            "repete o agrupamento pedido."
        ),
        parametros=(PERIODO, AGRUPAMENTO_DOS_ATRASOS),
    ),
}
