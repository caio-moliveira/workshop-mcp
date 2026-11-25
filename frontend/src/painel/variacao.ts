/**
 * A variação de um indicador em relação ao período anterior de mesmo tamanho. Contagens e receita
 * variam em termos relativos; taxas, em pontos percentuais; notas médias, em pontos da nota. Cada
 * forma tem o seu texto, e a seta e a cor seguem o que o texto mostra.
 */

import {
  formatarDiferencaDeNota,
  formatarPontosPercentuais,
  formatarVariacaoRelativa,
} from "../formatacao";

/** (atual − anterior) ÷ anterior. Sem anterior, ou com anterior zero, não há variação. */
export function variacaoRelativa(atual: number, anterior: number | null): number | null {
  if (anterior === null || anterior === 0) return null;
  return (atual - anterior) / anterior;
}

/** A diferença entre dois valores: duas taxas como fração (0,012 = 1,2 p.p.) ou duas notas. */
export function variacaoEmPontos(atual: number | null, anterior: number | null): number | null {
  if (atual === null || anterior === null) return null;
  return atual - anterior;
}

/**
 * Para qual lado o indicador melhora: pedidos sobem bem; a taxa de atraso, as reclamações e os
 * produtos mal avaliados descem bem.
 */
export type Melhora = "sobe" | "desce";

export type Tom = "bom" | "ruim" | "neutro";

export type Sentido = "sobe" | "desce" | "estavel";

/**
 * `relativa` para contagens e receita ("+8,5%"), `pontos_percentuais` para taxas ("+1,2 p.p.") e
 * `pontos` para notas médias ("+0,07").
 */
export type FormaDaVariacao = "relativa" | "pontos_percentuais" | "pontos";

/** A variação pronta para o cartão: o texto com sinal, a seta e a cor. */
export interface VariacaoDoIndicador {
  texto: string;
  sentido: Sentido;
  tom: Tom;
}

interface Forma {
  calcular: (atual: number | null, anterior: number | null) => number | null;
  formatar: (variacao: number) => string;
  /**
   * Abaixo disto a variação aparece como zero, e a cor e a seta não podem dizer outra coisa: meia
   * casa do texto. O percentual e os pontos percentuais têm uma casa (0,001 como fração); a nota,
   * duas.
   */
  menorVisivel: number;
}

const FORMAS: Record<FormaDaVariacao, Forma> = {
  relativa: {
    calcular: (atual, anterior) => (atual === null ? null : variacaoRelativa(atual, anterior)),
    formatar: formatarVariacaoRelativa,
    menorVisivel: 0.0005,
  },
  pontos_percentuais: {
    calcular: variacaoEmPontos,
    formatar: formatarPontosPercentuais,
    menorVisivel: 0.0005,
  },
  pontos: {
    calcular: variacaoEmPontos,
    formatar: formatarDiferencaDeNota,
    menorVisivel: 0.005,
  },
};

/** A variação de um indicador, ou `null` quando não há período anterior com que comparar. */
export function variacaoDoIndicador(
  atual: number | null,
  anterior: number | null,
  forma: FormaDaVariacao,
  melhora: Melhora,
): VariacaoDoIndicador | null {
  const { calcular, formatar, menorVisivel } = FORMAS[forma];
  const variacao = calcular(atual, anterior);
  if (variacao === null) return null;
  const texto = formatar(variacao);
  if (Math.abs(variacao) < menorVisivel) return { texto, sentido: "estavel", tom: "neutro" };
  const sentido = variacao > 0 ? "sobe" : "desce";
  return { texto, sentido, tom: sentido === melhora ? "bom" : "ruim" };
}
