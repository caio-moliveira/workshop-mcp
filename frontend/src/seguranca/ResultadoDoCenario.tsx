import { IconeAviso, IconeCadeado, IconeCheck } from "../componentes/icones";
import type { CenarioDeSeguranca } from "./contrato";
import estilos from "./ResultadoDoCenario.module.css";

/** O resultado com ícone e texto, nunca só a cor (FE §9), e a marca da divergência. */
export function ResultadoDoCenario({ cenario }: { cenario: CenarioDeSeguranca }) {
  const permitido = cenario.obtido === "permitido";
  return (
    <span className={estilos.resultado}>
      <span className={estilos.desfecho} data-desfecho={cenario.obtido}>
        {permitido ? <IconeCheck /> : <IconeCadeado />}
        {permitido ? "Permitido" : "Negado"}
      </span>
      {cenario.divergencia && (
        <span className={estilos.divergencia}>
          <IconeAviso />
          Divergência: esperado {cenario.esperado}
        </span>
      )}
    </span>
  );
}
