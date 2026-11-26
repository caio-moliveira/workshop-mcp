/** O que a gaveta lateral precisa de um elemento para mover o foco. */
export interface Focavel {
  focus(): void;
  isConnected?: boolean;
}

/**
 * Abre a gaveta lateral para o teclado: o foco vai para a gaveta e o Esc a fecha. Devolve a
 * função que solta a gaveta, que para de ouvir o Esc e devolve o foco à linha que a abriu, se ela
 * ainda estiver na página.
 */
export function abrirGaveta(
  teclado: EventTarget,
  gaveta: Focavel,
  origem: Focavel | null,
  aoFechar: () => void,
): () => void {
  gaveta.focus();
  const aoTeclar = (evento: Event) => {
    if ((evento as KeyboardEvent).key === "Escape") aoFechar();
  };
  teclado.addEventListener("keydown", aoTeclar);
  return () => {
    teclado.removeEventListener("keydown", aoTeclar);
    if (origem && origem.isConnected !== false) origem.focus();
  };
}
