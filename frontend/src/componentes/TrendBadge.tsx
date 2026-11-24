import type { Tom } from "../vendas/variacao";
import { IconeTendencia } from "./icones";
import estilos from "./TrendBadge.module.css";

interface Propriedades {
  /** A variação já formatada, com sinal: "+8,5%" ou "-1,2 p.p.". */
  texto: string;
  /** Para onde a variação foi: a seta. */
  sentido: "sobe" | "desce" | "estavel";
  /** Se a variação é boa ou ruim para o negócio: a cor, nunca sozinha (a seta e o texto bastam). */
  tom: Tom;
  /** Contra o que se compara, para leitores de tela e na dica. */
  comparacao: string;
}

/** Pequena variação de um indicador em relação ao período anterior (FE §6, §12). */
export function TrendBadge({ texto, sentido, tom, comparacao }: Propriedades) {
  return (
    <span className={`${estilos.variacao} ${estilos[tom]}`} title={comparacao}>
      {sentido !== "estavel" && <IconeTendencia sentido={sentido} />}
      {texto}
      <span className="visualmente-oculto"> {comparacao}</span>
    </span>
  );
}
