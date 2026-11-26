import { useSyncExternalStore } from "react";

/** O endereço do painel de segurança, que só existe com o interruptor de demonstração ligado. */
export const PAGINA_DE_SEGURANCA = "/seguranca";

function inscrever(aoMudar: () => void): () => void {
  window.addEventListener("popstate", aoMudar);
  return () => window.removeEventListener("popstate", aoMudar);
}

function caminhoAtual(): string {
  return window.location.pathname;
}

/** A página aberta, pelo caminho da URL. Fora do navegador (no teste), o painel do perfil. */
export function usePagina(): string {
  return useSyncExternalStore(inscrever, caminhoAtual, () => "/");
}

/**
 * Abre outra página sem recarregar a aplicação: grava a URL (o voltar do navegador volta à
 * anterior) e todo componente que usa `usePagina` vê a nova. O período não passa de uma página a
 * outra.
 */
export function irPara(caminho: string): void {
  if (window.location.pathname === caminho) return;
  window.history.pushState(null, "", caminho);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
