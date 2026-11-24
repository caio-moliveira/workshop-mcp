/**
 * O período de um painel: a janela que termina na data de referência dos dados (glossário). Fica
 * em `?periodo=` na URL, para recarregar ou compartilhar o link sem perder o filtro.
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

function ePeriodo(valor: unknown): valor is Periodo {
  return typeof valor === "string" && (PERIODOS as readonly string[]).includes(valor);
}

/** O período de uma busca da URL. Ausente ou inválido vira o padrão, sem erro. */
export function lerPeriodo(busca: string): Periodo {
  const valor = new URLSearchParams(busca).get("periodo");
  return ePeriodo(valor) ? valor : PERIODO_PADRAO;
}

/** A busca da URL com o período trocado e o resto mantido. */
export function buscaComPeriodo(busca: string, periodo: Periodo): string {
  const parametros = new URLSearchParams(busca);
  parametros.set("periodo", periodo);
  return `?${parametros.toString()}`;
}
