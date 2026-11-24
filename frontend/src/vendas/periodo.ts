import { eUmDe } from "./contrato";

/**
 * O período de um painel: os dias que terminam na data de referência dos dados (glossário). Fica
 * em `?periodo=` na URL, para recarregar ou compartilhar o link sem perder a escolha.
 */
export const PERIODOS = ["30d", "90d", "12m", "24m"] as const;

export type Periodo = (typeof PERIODOS)[number];

export const PERIODO_PADRAO: Periodo = "12m";

export const ROTULO_DO_PERIODO: Record<Periodo, string> = {
  "30d": "30 dias",
  "90d": "90 dias",
  "12m": "12 meses",
  "24m": "24 meses",
};

/** O período de uma busca da URL. Ausente ou inválido vira o padrão, sem erro. */
export function lerPeriodo(busca: string): Periodo {
  const valor = new URLSearchParams(busca).get("periodo");
  return eUmDe(PERIODOS, valor) ? valor : PERIODO_PADRAO;
}

/** A busca da URL com o período trocado e o resto mantido. */
export function buscaComPeriodo(busca: string, periodo: Periodo): string {
  const parametros = new URLSearchParams(busca);
  parametros.set("periodo", periodo);
  return `?${parametros.toString()}`;
}
