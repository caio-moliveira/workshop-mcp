import { useSyncExternalStore } from "react";

// A mesma fronteira do celular nos estilos (FE §11): abaixo dela, o painel já ocupa a tela inteira.
const TELA_LARGA = "(min-width: 768px)";

function assinar(avisar: () => void) {
  const consulta = window.matchMedia(TELA_LARGA);
  consulta.addEventListener("change", avisar);
  return () => consulta.removeEventListener("change", avisar);
}

/**
 * Se a tela comporta o modo expandido do assistente. Acompanha a largura ao vivo: estreitar a
 * janela com o modo expandido aberto volta ao painel em tela cheia, com o botão "Conversas".
 */
export function usePodeExpandir(): boolean {
  return useSyncExternalStore(
    assinar,
    () => window.matchMedia(TELA_LARGA).matches,
    () => true,
  );
}
