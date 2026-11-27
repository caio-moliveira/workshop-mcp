/** O contrato de `GET /diretoria/indicadores`: números crus e datas ISO. */

import {
  type Comparacao,
  type DatasDoPeriodo,
  eComparacao,
  eDatasDoPeriodo,
  eNotaOuNula,
  eObjeto,
  eSatisfacaoContada,
  eTaxaContada,
} from "../painel/contrato";

export interface IndicadoresDaDiretoria {
  periodo: DatasDoPeriodo;
  /** Pagamentos aprovados dos pedidos do período, com frete: o mesmo valor de Vendas. */
  receita: Comparacao<number>;
  /** Clientes com recompra ÷ clientes com pedido aprovado, de 0 a 1; `null` sem cliente. */
  taxa_de_recompra: Comparacao<number | null> & {
    clientes_com_recompra: number;
    clientes: number;
  };
  /** A nota média das avaliações do período, de 1 a 5; `null` sem avaliação. */
  satisfacao: Comparacao<number | null> & { avaliacoes: number };
  /**
   * Dos clientes do período anterior, a parte que comprou de novo no período, de 0 a 1. Tudo
   * `null` em 24 meses, que não tem período anterior nos dados; o `anterior` é `null` também em 12
   * meses, porque precisaria de dois períodos para trás.
   */
  retencao: {
    atual: number | null;
    anterior: number | null;
    retidos: number | null;
    clientes_do_periodo_anterior: number | null;
  };
}

function eTaxaDeRecompra(valor: unknown): boolean {
  return (
    eObjeto(valor) &&
    eComparacao(valor, true) &&
    eTaxaContada(valor.atual, valor.clientes_com_recompra, valor.clientes)
  );
}

function eSatisfacao(valor: unknown): boolean {
  return (
    eObjeto(valor) &&
    eComparacao(valor, true) &&
    eSatisfacaoContada(valor.atual, valor.avaliacoes) &&
    eNotaOuNula(valor.anterior)
  );
}

/** A retenção vazia de um período sem anterior: as quatro partes nulas. */
function eRetencaoVazia(valor: Record<string, unknown>): boolean {
  return (
    valor.atual === null &&
    valor.anterior === null &&
    valor.retidos === null &&
    valor.clientes_do_periodo_anterior === null
  );
}

function eRetencao(valor: unknown, temAnterior: boolean): boolean {
  if (!eObjeto(valor) || !eComparacao(valor, true) || !("retidos" in valor)) return false;
  if (!temAnterior) return eRetencaoVazia(valor);
  return eTaxaContada(valor.atual, valor.retidos, valor.clientes_do_periodo_anterior);
}

export function eIndicadoresDaDiretoria(valor: unknown): valor is IndicadoresDaDiretoria {
  if (!eObjeto(valor) || !eDatasDoPeriodo(valor.periodo)) return false;
  const { receita, taxa_de_recompra: recompra, satisfacao, retencao } = valor;
  if (!eComparacao(receita, false) || !eTaxaDeRecompra(recompra) || !eSatisfacao(satisfacao)) {
    return false;
  }
  // Sem período anterior nos dados (24 meses), nenhum indicador tem anterior.
  const temAnterior = (receita as Comparacao<number>).anterior !== null;
  const semAnterior = [recompra, satisfacao].every(
    (indicador) => (indicador as Comparacao<unknown>).anterior === null,
  );
  return (temAnterior || semAnterior) && eRetencao(retencao, temAnterior);
}
