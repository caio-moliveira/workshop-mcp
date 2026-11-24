/** Os validadores comuns aos contratos das rotas de Vendas: a resposta chega como `unknown`. */

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

export function eDataIso(valor: unknown): valor is string {
  return typeof valor === "string" && DATA_ISO.test(valor);
}

export function eUmDe<T extends string>(opcoes: readonly T[], valor: unknown): valor is T {
  return typeof valor === "string" && (opcoes as readonly string[]).includes(valor);
}

export function eDatasDoPeriodo(valor: unknown): valor is DatasDoPeriodo {
  return eObjeto(valor) && eDataIso(valor.inicio) && eDataIso(valor.fim);
}
