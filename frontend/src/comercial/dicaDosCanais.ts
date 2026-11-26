/** A série e a dica do gráfico de novos lojistas por canal. */

import { type LinhaDaDica, SO_NA_DICA, type SerieDoGrafico } from "../componentes/graficos";
import { formatarNumero, formatarPercentual } from "../formatacao";
import type { DesempenhoDoCanal } from "./desempenhoDosCanais";

export const NOVOS_LOJISTAS: SerieDoGrafico = {
  rotulo: "Novos lojistas",
  cor: "var(--serie-1)",
  forma: "barra",
};

/**
 * As linhas da dica de um canal: os novos lojistas, a conversão e os leads que a acompanham, para
 * a base pequena ficar à vista.
 */
export function linhasDaDica(item: DesempenhoDoCanal): LinhaDaDica[] {
  return [
    { ...NOVOS_LOJISTAS, valor: formatarNumero(item.novos_lojistas) },
    // A conversão e os leads só aparecem na dica.
    {
      ...SO_NA_DICA,
      rotulo: "Conversão",
      valor: item.conversao === null ? "—" : formatarPercentual(item.conversao),
    },
    { ...SO_NA_DICA, rotulo: "Leads do período", valor: formatarNumero(item.leads) },
  ];
}
