import type { ReactNode } from "react";

import estilos from "./KpiCard.module.css";

interface Propriedades {
  rotulo: string;
  /** O valor já formatado, em destaque. */
  valor: string;
  /** Legenda curta sob o valor. */
  legenda: string;
  /** A variação em relação ao período anterior (um TrendBadge), quando existe. */
  variacao?: ReactNode;
}

/** Cartão de indicador: valor em destaque, legenda e pequena variação (FE §6, §12). */
export function KpiCard({ rotulo, valor, legenda, variacao }: Propriedades) {
  return (
    <article className={estilos.cartao}>
      <h3 className={estilos.rotulo}>{rotulo}</h3>
      <p className={estilos.valor}>{valor}</p>
      <div className={estilos.rodape}>
        {variacao}
        <p className={estilos.legenda}>{legenda}</p>
      </div>
    </article>
  );
}
