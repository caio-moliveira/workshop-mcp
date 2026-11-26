/** O contrato de `GET /vendas/indicadores`: números crus e datas ISO. */

import {
  type Comparacao,
  type DatasDoPeriodo,
  eComparacao,
  eDatasDoPeriodo,
  eNumero,
  eObjeto,
} from "../painel/contrato";

export interface IndicadoresDeVendas {
  periodo: DatasDoPeriodo;
  pedidos_realizados: Comparacao<number>;
  receita: Comparacao<number>;
  /** Taxas são frações de 0 a 1; `null` quando o período não tem denominador. */
  taxa_de_atraso: Comparacao<number | null> & { atrasos: number };
  taxa_de_aprovacao: Comparacao<number | null>;
}

export function eIndicadoresDeVendas(valor: unknown): valor is IndicadoresDeVendas {
  if (!eObjeto(valor)) return false;
  const { taxa_de_atraso: taxaDeAtraso } = valor;
  return (
    eDatasDoPeriodo(valor.periodo) &&
    eComparacao(valor.pedidos_realizados, false) &&
    eComparacao(valor.receita, false) &&
    eComparacao(taxaDeAtraso, true) &&
    eObjeto(taxaDeAtraso) &&
    eNumero(taxaDeAtraso.atrasos) &&
    eComparacao(valor.taxa_de_aprovacao, true)
  );
}
