/** As etapas do funil (glossário), na ordem do funil e com Perdido por último, como a API as devolve. */
export const ETAPAS = [
  "Novo",
  "Contatado",
  "Qualificado",
  "Proposta",
  "Fechado",
  "Perdido",
] as const;

export type Etapa = (typeof ETAPAS)[number];

/** O lead que virou lojista: a única etapa com data de fechamento. */
export const FECHADO = "Fechado" satisfies Etapa;
/** Não é uma etapa seguinte a Fechado: fica por último no funil. */
export const PERDIDO = "Perdido" satisfies Etapa;
