/** Os canais por onde um lead chega (glossário), como a API os devolve. */
export const CANAIS = [
  "Indicação",
  "Orgânico",
  "Mídia paga",
  "Eventos",
  "Prospecção ativa",
] as const;

export type Canal = (typeof CANAIS)[number];
