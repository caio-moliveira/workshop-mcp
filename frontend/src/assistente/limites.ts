/**
 * O teto de caracteres da pergunta, conferido no navegador antes do envio.
 *
 * É o padrão de `LIMITE_DE_CARACTERES_DA_PERGUNTA` no backend (`backend/assistente/limites.py`).
 * Quem mudar a variável no ambiente da API muda também esta constante: o backend segue sendo quem
 * decide, e uma pergunta acima do teto dele volta como 400.
 */
export const LIMITE_DE_CARACTERES_DA_PERGUNTA = 2000;

/** Os caracteres que seguem para a API: sem os espaços das pontas, contados como o Python conta. */
export function caracteresDaPergunta(pergunta: string): number {
  return [...pergunta.trim()].length;
}

export function passouDoLimite(pergunta: string): boolean {
  return caracteresDaPergunta(pergunta) > LIMITE_DE_CARACTERES_DA_PERGUNTA;
}
