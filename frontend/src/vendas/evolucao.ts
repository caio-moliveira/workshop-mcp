/** O contrato de `GET /vendas/evolucao`: números crus e datas ISO. */

/** Dia em 30 dias, semana (começando na segunda) em 90 dias, mês em 12 e 24 meses. */
export type Agrupamento = "dia" | "semana" | "mes";

export interface PontoDaEvolucao {
  /** O primeiro dia do intervalo de calendário (a segunda da semana, o dia 1 do mês). */
  inicio: string;
  pedidos: number;
  receita: number;
}

export interface EvolucaoDeVendas {
  agrupamento: Agrupamento;
  /** Em ordem, um por intervalo do período, com zero onde não houve pedido. */
  pontos: PontoDaEvolucao[];
}

const AGRUPAMENTOS: readonly string[] = ["dia", "semana", "mes"];
const DATA_ISO = /^\d{4}-\d{2}-\d{2}$/;
const MESES = [
  "janeiro",
  "fevereiro",
  "março",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];

function eObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

function eNumero(valor: unknown): valor is number {
  return typeof valor === "number" && Number.isFinite(valor);
}

function ePonto(valor: unknown): valor is PontoDaEvolucao {
  return (
    eObjeto(valor) &&
    typeof valor.inicio === "string" &&
    DATA_ISO.test(valor.inicio) &&
    Number.isInteger(valor.pedidos) &&
    eNumero(valor.receita)
  );
}

export function eEvolucaoDeVendas(valor: unknown): valor is EvolucaoDeVendas {
  return (
    eObjeto(valor) &&
    typeof valor.agrupamento === "string" &&
    AGRUPAMENTOS.includes(valor.agrupamento) &&
    Array.isArray(valor.pontos) &&
    valor.pontos.every(ePonto)
  );
}

/** Nenhum pedido em nenhum intervalo: o bloco mostra o estado vazio. */
export function semPedidos(evolucao: EvolucaoDeVendas): boolean {
  return evolucao.pontos.every((ponto) => ponto.pedidos === 0);
}

/** Ano, mês e dia de uma data ISO, sem passar por `Date` e pelo fuso do navegador. */
function partes(iso: string): { ano: string; mes: string; dia: string; nomeDoMes: string } {
  const [ano = "", mes = "", dia = ""] = iso.split("-");
  return { ano, mes, dia, nomeDoMes: MESES[Number(mes) - 1] ?? mes };
}

/** O rótulo curto do eixo: "02/11" para dia e semana, "dez/25" para mês. */
export function rotuloDoEixo(inicio: string, agrupamento: Agrupamento): string {
  const { ano, mes, dia, nomeDoMes } = partes(inicio);
  if (agrupamento === "mes") return `${nomeDoMes.slice(0, 3)}/${ano.slice(2)}`;
  return `${dia}/${mes}`;
}

/** O intervalo por extenso, para a dica: "02/11/2026", "Semana de 31/08/2026", "Dezembro de 2025". */
export function rotuloDoIntervalo(inicio: string, agrupamento: Agrupamento): string {
  const { ano, mes, dia, nomeDoMes } = partes(inicio);
  const data = `${dia}/${mes}/${ano}`;
  if (agrupamento === "dia") return data;
  if (agrupamento === "semana") return `Semana de ${data}`;
  return `${nomeDoMes.charAt(0).toUpperCase()}${nomeDoMes.slice(1)} de ${ano}`;
}
