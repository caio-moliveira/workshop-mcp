/** As etapas do funil (glossário), na ordem do funil, com Perdido por último, como a API as devolve. */
export const ETAPAS = [
  "Novo",
  "Contatado",
  "Qualificado",
  "Proposta",
  "Fechado",
  "Perdido",
] as const;

export type Etapa = (typeof ETAPAS)[number];
