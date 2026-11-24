/** O contrato de `GET /vendas/indicadores`: números crus e datas ISO. */

/** O valor do período e o do anterior de mesmo tamanho (`null` quando não há anterior). */
export interface Comparacao<T> {
  atual: T;
  anterior: T | null;
}

export interface IndicadoresDeVendas {
  periodo: { inicio: string; fim: string };
  pedidos_realizados: Comparacao<number>;
  receita: Comparacao<number>;
  /** Taxas são frações de 0 a 1; `null` quando o período não tem denominador. */
  taxa_de_atraso: Comparacao<number | null> & { atrasos: number };
  taxa_de_aprovacao: Comparacao<number | null>;
}

const DATA_ISO = /^\d{4}-\d{2}-\d{2}$/;

function eObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

function eNumero(valor: unknown): valor is number {
  return typeof valor === "number" && Number.isFinite(valor);
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
  if (!eObjeto(valor) || !eObjeto(valor.periodo)) return false;
  const { inicio, fim } = valor.periodo;
  const { taxa_de_atraso: taxaDeAtraso } = valor;
  return (
    typeof inicio === "string" &&
    DATA_ISO.test(inicio) &&
    typeof fim === "string" &&
    DATA_ISO.test(fim) &&
    eComparacao(valor.pedidos_realizados, false) &&
    eComparacao(valor.receita, false) &&
    eComparacao(taxaDeAtraso, true) &&
    eObjeto(taxaDeAtraso) &&
    eNumero(taxaDeAtraso.atrasos) &&
    eComparacao(valor.taxa_de_aprovacao, true)
  );
}
