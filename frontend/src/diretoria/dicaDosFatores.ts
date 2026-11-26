/** As séries e as dicas dos gráficos dos fatores de recompra. */

import { type LinhaDaDica, SO_NA_DICA, type SerieDoGrafico } from "../componentes/graficos";
import { formatarNota, formatarNumero, formatarPercentual } from "../formatacao";
import type { GrupoDeRecompra, GrupoDeSatisfacao } from "./fatores";

export const TAXA_DE_RECOMPRA: SerieDoGrafico = {
  rotulo: "Taxa de recompra",
  cor: "var(--serie-1)",
  forma: "barra",
};
export const SATISFACAO: SerieDoGrafico = {
  rotulo: "Satisfação",
  cor: "var(--serie-2)",
  forma: "barra",
};

/** A dica de um grupo de recompra: a taxa e o tamanho do grupo sobre o qual ela foi calculada. */
export function linhasDaDicaDeRecompra(item: GrupoDeRecompra): LinhaDaDica[] {
  return [
    {
      ...TAXA_DE_RECOMPRA,
      valor: item.taxa_de_recompra === null ? "—" : formatarPercentual(item.taxa_de_recompra),
    },
    {
      ...SO_NA_DICA,
      rotulo: "Clientes com recompra",
      valor: formatarNumero(item.clientes_com_recompra),
    },
    {
      ...SO_NA_DICA,
      rotulo: "Clientes do grupo",
      valor: formatarNumero(item.clientes),
    },
  ];
}

/** A dica de uma faixa de atraso: a satisfação e quantas avaliações ela resume. */
export function linhasDaDicaDeSatisfacao(item: GrupoDeSatisfacao): LinhaDaDica[] {
  return [
    {
      ...SATISFACAO,
      valor: item.satisfacao === null ? "—" : formatarNota(item.satisfacao),
    },
    {
      ...SO_NA_DICA,
      rotulo: "Avaliações do grupo",
      valor: formatarNumero(item.avaliacoes),
    },
  ];
}
