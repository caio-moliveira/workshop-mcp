import { useSyncExternalStore } from "react";

import { buscaComPeriodo, lerPeriodo, type Periodo } from "./periodo";

function inscrever(aoMudar: () => void): () => void {
  window.addEventListener("popstate", aoMudar);
  return () => window.removeEventListener("popstate", aoMudar);
}

function buscaAtual(): string {
  return window.location.search;
}

/**
 * O período em `?periodo=` da URL. Trocar o período grava a URL (o voltar do navegador volta ao
 * anterior) e todo componente que usa este hook vê o novo valor.
 */
export function usePeriodoDaUrl(): [Periodo, (periodo: Periodo) => void] {
  const periodo = lerPeriodo(useSyncExternalStore(inscrever, buscaAtual));
  const mudar = (novo: Periodo) => {
    const { pathname, search, hash } = window.location;
    window.history.pushState(null, "", `${pathname}${buscaComPeriodo(search, novo)}${hash}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  };
  return [periodo, mudar];
}
