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
    "vendas_evolucao": Ferramenta(
        consulta=vendas.evolucao,
        titulo="Evolução de Vendas",
        descricao=(
            "Série temporal de Vendas em um período: pedidos realizados e receita de cada dia, "
            "semana ou mês, em ordem cronológica. Use para ver tendência, sazonalidade, picos e "
            "quedas, ou para saber quando as vendas subiram ou caíram; para o total do período e "
            "a comparação com o período anterior, use vendas_indicadores. O agrupamento depende "
            "do período e vem no campo 'agrupamento': 'dia' para '30d', 'semana' para '90d' e "
            "'mes' para '12m' e '24m'. Cada item de 'pontos' traz 'inicio' (data ISO do primeiro "
            "dia daquele dia, semana ou mês de calendário; a semana começa na segunda-feira e o "
            "mês no dia 1), 'pedidos' (pedidos realizados) e 'receita' (soma dos pagamentos "
            "aprovados, em reais). Só os pedidos do período entram: quando o período começa no "
            "meio de uma semana ou de um mês, o primeiro ponto é parcial e não deve ser lido "
            "como queda. Pontos sem pedidos aparecem com zero."
        ),
        parametros=(PERIODO,),
    ),
    "vendas_situacao_das_entregas": Ferramenta(
        consulta=vendas.situacao_das_entregas,
        titulo="Situação das entregas",
        descricao=(
            "Quantos pedidos de um período estão em cada situação de entrega. Use para saber "
            "como estão as entregas: quantas já chegaram, quantas chegaram com atraso e quantas "
            "ainda estão a caminho; para a taxa de atraso e sua comparação com o período "
            "anterior, use vendas_indicadores. 'situacoes' traz sempre as quatro situações, "
            "nesta ordem, mesmo as que têm zero pedidos: 'Em trânsito' (ainda não entregue, "
            "dentro do prazo), 'Prazo vencido' (ainda não entregue e a data prometida já passou "
            "na data de referência dos dados), 'Entregue no prazo' e 'Entregue com atraso' "
            "(entregue depois da data prometida). Prazo vencido não é atraso: atraso só existe "
            "em pedido já entregue, e pedidos com prazo vencido não entram na taxa de atraso. "
            "Pedidos com pagamento recusado não têm entrega e não aparecem em nenhuma situação, "
            "então a soma das quatro é menor que o total de pedidos realizados. 'periodo' traz "
            "as datas de início e fim usadas, em formato ISO."
        ),
        parametros=(PERIODO,),
    ),
    "vendas_pedidos_recentes": Ferramenta(
        consulta=vendas.pedidos_recentes,
        titulo="Pedidos recentes",
        descricao=(
            "Os pedidos mais recentes de um período, do mais novo para o mais antigo. Use para "
            "ver exemplos concretos de pedidos: o que foi comprado por último, de qual lojista, "
            "em qual rota, por quanto e em que situação. A lista é limitada aos 20 pedidos mais "
            "recentes e não é o total do período: não some nem conte a partir dela; para "
            "totais, taxas, tendência ou contagem por situação de entrega, use as outras "
            "ferramentas de Vendas. Cada item de 'pedidos' traz 'numero' (número do pedido), "
            "'momento_compra' (instante da compra, ISO com fuso; o dia do pedido é o do horário "
            "de Brasília), 'cidade' e 'uf' (do cliente; nenhum outro dado do cliente é "
            "devolvido), 'lojista' (nome do lojista), 'rota' (UF do lojista → UF do cliente), "
            "'valor' (valor do pagamento em reais, com itens e frete), 'pagamento' ('Aprovado' "
            "ou 'Recusado') e 'entrega' ('Em trânsito', 'Prazo vencido', 'Entregue no prazo' ou "
            "'Entregue com atraso'; nulo quando o pagamento foi recusado, porque não há "
            "entrega). Prazo vencido é pedido ainda não entregue com a data prometida já "
            "passada; não é atraso. 'periodo' traz as datas de início e fim usadas, em formato "
            "ISO."
        ),
        parametros=(PERIODO,),
    ),
}
