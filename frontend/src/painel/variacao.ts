/**
 * A variação de um indicador em relação ao período anterior de mesmo tamanho. Contagens e receita
 * variam em termos relativos; taxas, em pontos percentuais, para não confundir as duas.
 */

/** (atual − anterior) ÷ anterior. Sem anterior, ou com anterior zero, não há variação. */
export function variacaoRelativa(atual: number, anterior: number | null): number | null {
  if (anterior === null || anterior === 0) return null;
  return (atual - anterior) / anterior;
}

/** A diferença entre duas taxas, como fração (0,012 = 1,2 p.p.). */
export function variacaoEmPontos(atual: number | null, anterior: number | null): number | null {
  if (atual === null || anterior === null) return null;
  return atual - anterior;
}

/** Para qual lado o indicador melhora: pedidos sobem bem, a taxa de atraso desce bem. */
export type Melhora = "sobe" | "desce";

export type Tom = "bom" | "ruim" | "neutro";

/**
 * As duas variações aparecem com uma casa: 0,1% ou 0,1 p.p., ou seja, 0,001 como fração. Abaixo da
 * metade disso a variação aparece como zero, e a cor e a seta não podem dizer outra coisa.
 */
const MENOR_VARIACAO_VISIVEL = 0.0005;

function pareceZero(variacao: number): boolean {
  return Math.abs(variacao) < MENOR_VARIACAO_VISIVEL;
}

export function tomDaVariacao(variacao: number, melhora: Melhora): Tom {
  if (pareceZero(variacao)) return "neutro";
  return variacao > 0 === (melhora === "sobe") ? "bom" : "ruim";
}

/** Para onde aponta a seta: a mesma regra do tom, para os dois concordarem com o texto. */
export function sentidoDaVariacao(variacao: number): "sobe" | "desce" | "estavel" {
  if (pareceZero(variacao)) return "estavel";
  return variacao > 0 ? "sobe" : "desce";
}
