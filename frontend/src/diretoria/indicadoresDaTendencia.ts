/** Os quatro indicadores da tendência, como a tela os mostra: a série, o valor e a dica. */

import { SO_NA_DICA, type SerieDoGrafico } from "../componentes/graficos";
import {
  formatarMoeda,
  formatarMoedaCompacta,
  formatarNota,
  formatarNumero,
  formatarPercentual,
} from "../formatacao";
import type { PontoDaTendencia } from "./tendencia";

export type LinhaDaDica = SerieDoGrafico & { valor: string };

/** Um dos quatro indicadores da tendência: a série, como ler o valor e de que base ele saiu. */
export interface IndicadorDaTendencia {
  rotulo: string;
  serie: SerieDoGrafico;
  valor: (ponto: PontoDaTendencia) => number | null;
  /** O valor por extenso, já formatado. */
  formatar: (valor: number) => string;
  formatarEixo: (valor: number) => string;
  /** O que diz o ponto vazio, na descrição em texto. */
  vazio: string;
  /** A base do ponto, na dica, sem cor de série própria. */
  base?: (ponto: PontoDaTendencia) => { rotulo: string; valor: string };
  dominio?: [number, number];
}

function linha(rotulo: string, cor: string): SerieDoGrafico {
  return { rotulo, cor, forma: "linha" };
}

function percentualDoEixo(fracao: number): string {
  return formatarPercentual(fracao).replace(",0%", "%");
}

export const INDICADORES: IndicadorDaTendencia[] = [
  {
    rotulo: "Receita",
    serie: linha("Receita", "var(--serie-1)"),
    valor: (ponto) => ponto.receita,
    formatar: formatarMoeda,
    formatarEixo: formatarMoedaCompacta,
    vazio: "sem receita",
  },
  {
    rotulo: "Taxa de recompra",
    serie: linha("Taxa de recompra", "var(--serie-2)"),
    valor: (ponto) => ponto.taxa_de_recompra,
    formatar: formatarPercentual,
    formatarEixo: percentualDoEixo,
    vazio: "sem cliente",
    base: (ponto) => ({
      rotulo: "Clientes com recompra",
      valor: `${formatarNumero(ponto.clientes_com_recompra)} de ${formatarNumero(ponto.clientes)}`,
    }),
  },
  {
    rotulo: "Satisfação",
    serie: linha("Nota média", "var(--serie-3)"),
    valor: (ponto) => ponto.satisfacao,
    formatar: formatarNota,
    formatarEixo: formatarNota,
    vazio: "sem avaliação",
    base: (ponto) => ({ rotulo: "Avaliações", valor: formatarNumero(ponto.avaliacoes) }),
  },
  {
    rotulo: "Taxa de atraso",
    serie: linha("Taxa de atraso", "var(--serie-4)"),
    valor: (ponto) => ponto.taxa_de_atraso,
    formatar: formatarPercentual,
    formatarEixo: percentualDoEixo,
    vazio: "sem pedido entregue",
    base: (ponto) => ({
      rotulo: "Entregues com atraso",
      valor: `${formatarNumero(ponto.atrasos)} de ${formatarNumero(ponto.entregues)}`,
    }),
  },
];

/** As linhas da dica de um ponto: o valor do indicador e, quando há, a base de que ele saiu. */
export function linhasDaDica(indicador: IndicadorDaTendencia, ponto: PontoDaTendencia): LinhaDaDica[] {
  const valor = indicador.valor(ponto);
  const linhas: LinhaDaDica[] = [
    { ...indicador.serie, valor: valor === null ? "—" : indicador.formatar(valor) },
  ];
  if (indicador.base) linhas.push({ ...SO_NA_DICA, ...indicador.base(ponto) });
  return linhas;
}
