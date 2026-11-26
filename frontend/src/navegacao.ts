import { useSyncExternalStore } from "react";

import type { UsuarioAutenticado } from "./api";
import { DESCRICAO_DOS_PERFIS } from "./perfis";

/** O endereço do painel de segurança, que só existe com o interruptor de demonstração ligado. */
export const PAGINA_DE_SEGURANCA = "/seguranca";

/**
 * Se a página aberta é a de segurança. Sem o interruptor de demonstração, `/seguranca` mostra o
 * painel do perfil, como qualquer outro caminho.
 */
export function naPaginaDeSeguranca(usuario: UsuarioAutenticado, pagina: string): boolean {
  return usuario.painel_de_seguranca === true && pagina === PAGINA_DE_SEGURANCA;
}

/** O nome da página aberta, no caminho do topo: Segurança ou o nome do perfil. */
export function rotuloDaPagina(usuario: UsuarioAutenticado, pagina: string): string {
  return naPaginaDeSeguranca(usuario, pagina)
    ? "Segurança"
    : DESCRICAO_DOS_PERFIS[usuario.perfil].nome;
}

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
