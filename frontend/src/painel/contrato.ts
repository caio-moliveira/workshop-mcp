/** Os validadores comuns aos contratos das rotas de dados dos painéis: a resposta chega como `unknown`. */

/** Os dias de um período, de `inicio` a `fim`, inclusive, em datas ISO. */
export interface DatasDoPeriodo {
  inicio: string;
  fim: string;
}

export const DATA_ISO = /^\d{4}-\d{2}-\d{2}$/;

export function eObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

export function eNumero(valor: unknown): valor is number {
  return typeof valor === "number" && Number.isFinite(valor);
}

/** Uma contagem: um inteiro de zero em diante. */
export function eContagem(valor: unknown): valor is number {
  return Number.isInteger(valor) && (valor as number) >= 0;
}

/** Um texto não vazio. */
export function eTexto(valor: unknown): valor is string {
  return typeof valor === "string" && valor !== "";
}

export function eDataIso(valor: unknown): valor is string {
  return typeof valor === "string" && DATA_ISO.test(valor);
}

export function eUmDe<T extends string>(opcoes: readonly T[], valor: unknown): valor is T {
  return typeof valor === "string" && (opcoes as readonly string[]).includes(valor);
}

export function eDatasDoPeriodo(valor: unknown): valor is DatasDoPeriodo {
  return eObjeto(valor) && eDataIso(valor.inicio) && eDataIso(valor.fim);
}

/** O valor do período e o do anterior de mesmo tamanho (`null` quando não há anterior). */
export interface Comparacao<T> {
  atual: T;
  anterior: T | null;
}

export function eNumeroOuNulo(valor: unknown): valor is number | null {
  return valor === null || eNumero(valor);
}

/** Uma `Comparacao` de números; o atual pode ser `null` quando o período não tem denominador. */
export function eComparacao(valor: unknown, atualPodeSerNulo: boolean): boolean {
  if (!eObjeto(valor) || !("anterior" in valor)) return false;
  const atualValido = atualPodeSerNulo ? eNumeroOuNulo(valor.atual) : eNumero(valor.atual);
  return atualValido && eNumeroOuNulo(valor.anterior);
}
