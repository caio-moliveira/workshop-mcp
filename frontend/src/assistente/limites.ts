/**
 * O teto de caracteres da pergunta, conferido no navegador antes do envio.
 *
 * É o padrão de `LIMITE_DE_CARACTERES_DA_PERGUNTA` no backend (`backend/assistente/limites.py`).
 * Quem mudar a variável no ambiente da API muda também esta constante: o backend segue sendo quem
 * decide, e uma pergunta acima do teto dele volta como 400.
 */
export const LIMITE_DE_CARACTERES_DA_PERGUNTA = 2000;

/**
 * Quantos itens da conversa anterior a API aceita com a pergunta: `ITENS_DA_CONVERSA` em
 * `backend/assistente/limites.py`. Cada item fica também dentro do teto de caracteres acima.
 */
export const ITENS_DA_CONVERSA = 20;

/** O sinal no fim do texto cortado para caber no teto de caracteres. */
export const MARCA_DE_CORTE = "…";

/** O texto dentro do teto de caracteres, contados como o Python conta; cortado, ganha a marca. */
export function cortarNoLimite(texto: string): string {
  const caracteres = [...texto];
  if (caracteres.length <= LIMITE_DE_CARACTERES_DA_PERGUNTA) return texto;
  return caracteres.slice(0, LIMITE_DE_CARACTERES_DA_PERGUNTA - 1).join("") + MARCA_DE_CORTE;
}

/** Os caracteres que seguem para a API: sem os espaços das pontas, contados como o Python conta. */
export function caracteresDaPergunta(pergunta: string): number {
  return [...pergunta.trim()].length;
}

export function passouDoLimite(pergunta: string): boolean {
  return caracteresDaPergunta(pergunta) > LIMITE_DE_CARACTERES_DA_PERGUNTA;
}
