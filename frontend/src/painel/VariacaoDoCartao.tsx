import { TrendBadge } from "../componentes/TrendBadge";
import { ROTULO_DO_PERIODO, type Periodo } from "./periodo";
import type { VariacaoDoIndicador } from "./variacao";

/** A variação de um cartão de indicador, ou nada quando não há período anterior com que comparar. */
export function VariacaoDoCartao({
  variacao,
  periodo,
}: {
  variacao: VariacaoDoIndicador | null;
  periodo: Periodo;
}) {
  if (variacao === null) return null;
  return (
    <TrendBadge
      {...variacao}
      comparacao={`em relação aos ${ROTULO_DO_PERIODO[periodo]} anteriores`}
    />
  );
}
