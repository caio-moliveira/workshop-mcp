import { PERIODOS, ROTULO_DO_PERIODO, type Periodo } from "../vendas/periodo";
import estilos from "./PeriodFilter.module.css";

interface Propriedades {
  periodo: Periodo;
  aoMudar: (periodo: Periodo) => void;
}

/** Seletor de período: quatro opções fixas, uma pressionada (FE §5, §12). */
export function PeriodFilter({ periodo, aoMudar }: Propriedades) {
  return (
    <div className={estilos.filtro} role="group" aria-label="Período">
      {PERIODOS.map((opcao) => (
        <button
          key={opcao}
          type="button"
          className={estilos.opcao}
          aria-pressed={opcao === periodo}
          onClick={() => opcao !== periodo && aoMudar(opcao)}
        >
          {ROTULO_DO_PERIODO[opcao]}
        </button>
      ))}
    </div>
  );
}
