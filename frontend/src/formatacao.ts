/** Formatação em pt-BR dos números crus e datas ISO que a API devolve. */

const MOEDA = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const NUMERO = new Intl.NumberFormat("pt-BR");
const UMA_CASA = { minimumFractionDigits: 1, maximumFractionDigits: 1 } as const;
const PERCENTUAL = new Intl.NumberFormat("pt-BR", { style: "percent", ...UMA_CASA });
const PERCENTUAL_COM_SINAL = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  signDisplay: "exceptZero",
  ...UMA_CASA,
});
const PONTOS_COM_SINAL = new Intl.NumberFormat("pt-BR", { signDisplay: "exceptZero", ...UMA_CASA });

export function formatarMoeda(valor: number): string {
  return MOEDA.format(valor);
}

export function formatarNumero(valor: number): string {
  return NUMERO.format(valor);
}

/** Uma fração (0,123) como percentual com uma casa ("12,3%"). */
export function formatarPercentual(fracao: number): string {
  return PERCENTUAL.format(fracao);
}

/** Uma variação relativa (0,085) com sinal ("+8,5%"). */
export function formatarVariacaoRelativa(fracao: number): string {
  return PERCENTUAL_COM_SINAL.format(fracao);
}

/** A diferença entre duas taxas (0,012) em pontos percentuais, com sinal ("+1,2 p.p."). */
export function formatarPontosPercentuais(diferenca: number): string {
  return `${PONTOS_COM_SINAL.format(diferenca * 100)} p.p.`;
}

// O fuso do negócio: os dias do painel são os de Brasília, não os do navegador.
const DATA_HORA = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "America/Sao_Paulo",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** Um instante ISO com fuso ("2026-11-30T17:05:09+00:00") em data e hora de Brasília. */
export function formatarDataHora(iso: string): string {
  return DATA_HORA.format(new Date(iso));
}

/** Uma data ISO ("2026-11-30") no formato brasileiro, sem passar por fuso horário. */
export function formatarData(iso: string): string {
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}
