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

export function tomDaVariacao(variacao: number, melhora: Melhora): Tom {
  if (variacao === 0) return "neutro";
  return variacao > 0 === (melhora === "sobe") ? "bom" : "ruim";
}
