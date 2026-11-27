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

/** Uma fração de 0 a 1. */
export function eFracao(valor: unknown): valor is number {
  return eNumero(valor) && valor >= 0 && valor <= 1;
}

/** Uma taxa de 0 a 1 com a parte e o todo contados: vazia exatamente quando o todo é zero. */
export function eTaxaContada(taxa: unknown, parte: unknown, todo: unknown): boolean {
  if (!eContagem(parte) || !eContagem(todo) || parte > todo) return false;
  return todo === 0 ? taxa === null : eFracao(taxa);
}

const NOTA_MINIMA = 1;
const NOTA_MAXIMA = 5;

/** Uma nota média de 1 a 5, ou `null`. */
export function eNotaOuNula(valor: unknown): valor is number | null {
  return valor === null || (eNumero(valor) && valor >= NOTA_MINIMA && valor <= NOTA_MAXIMA);
}

/** A nota média das avaliações contadas: vazia exatamente quando não há avaliação. */
export function eSatisfacaoContada(nota: unknown, avaliacoes: unknown): boolean {
  if (!eContagem(avaliacoes) || !eNotaOuNula(nota)) return false;
  return (nota === null) === (avaliacoes === 0);
}
