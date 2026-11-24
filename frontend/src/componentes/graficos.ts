/**
 * O que todo gráfico do Recharts usa para seguir o FE §7: grade horizontal fina, eixos em cinza
 * secundário de 12 px e nenhuma animação longa. As cores vêm dos tokens, nunca soltas.
 */

/** Uma série de um gráfico, como aparece na legenda do ChartPanel e na dica. */
export interface SerieDoGrafico {
  rotulo: string;
  /** Um token de cor, como `var(--serie-1)`. */
  cor: string;
  forma: "barra" | "linha";
}

/** Só as linhas horizontais da grade, finas. */
export const GRADE = {
  vertical: false,
  stroke: "var(--grade-do-grafico)",
  strokeWidth: 1,
} as const;

/** Eixos sem linha nem marcação, rótulos em cinza secundário de 12 px. */
export const EIXO = {
  axisLine: false,
  tickLine: false,
  tick: { fill: "var(--text-secondary)", fontSize: 12 },
} as const;

/** O realce discreto do intervalo sob o ponteiro. */
export const CURSOR = { fill: "var(--surface-muted)" } as const;

/** Desligada: o FE §7 evita animações longas, e o painel já entra com opacidade (FE §10). */
export const SEM_ANIMACAO = { isAnimationActive: false } as const;
