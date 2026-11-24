/** O contrato de `GET /vendas/indicadores`: números crus e datas ISO. */

import { type DatasDoPeriodo, eDatasDoPeriodo, eNumero, eObjeto } from "./contrato";

/** O valor do período e o do anterior de mesmo tamanho (`null` quando não há anterior). */
export interface Comparacao<T> {
  atual: T;
  anterior: T | null;
}

export interface IndicadoresDeVendas {
  periodo: DatasDoPeriodo;
  pedidos_realizados: Comparacao<number>;
  receita: Comparacao<number>;
  /** Taxas são frações de 0 a 1; `null` quando o período não tem denominador. */
  taxa_de_atraso: Comparacao<number | null> & { atrasos: number };
  taxa_de_aprovacao: Comparacao<number | null>;
}

function eNumeroOuNulo(valor: unknown): valor is number | null {
  return valor === null || eNumero(valor);
}

function eComparacao(valor: unknown, atualPodeSerNulo: boolean): boolean {
  if (!eObjeto(valor) || !("anterior" in valor)) return false;
  const atualValido = atualPodeSerNulo ? eNumeroOuNulo(valor.atual) : eNumero(valor.atual);
  return atualValido && eNumeroOuNulo(valor.anterior);
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
