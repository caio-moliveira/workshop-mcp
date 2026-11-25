/** O contrato de `GET /vendas/evolucao`: números crus e datas ISO. */

import {
  type DatasDoPeriodo,
  eDataIso,
  eDatasDoPeriodo,
  eNumero,
  eObjeto,
  eUmDe,
} from "../painel/contrato";

/** Dia em 30 dias, semana (começando na segunda) em 90 dias, mês em 12 e 24 meses. */
export const AGRUPAMENTOS = ["dia", "semana", "mes"] as const;

export type Agrupamento = (typeof AGRUPAMENTOS)[number];

export interface PontoDaEvolucao {
  /** O primeiro dia do ponto no calendário (a segunda da semana, o dia 1 do mês). */
  inicio: string;
  pedidos: number;
  receita: number;
}

export interface EvolucaoDeVendas {
  periodo: DatasDoPeriodo;
  agrupamento: Agrupamento;
  /** Em ordem, um por dia, semana ou mês do período, com zero onde não houve pedido. */
  pontos: PontoDaEvolucao[];
}

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

function ePonto(valor: unknown): valor is PontoDaEvolucao {
  return (
    eObjeto(valor) &&
    eDataIso(valor.inicio) &&
    Number.isInteger(valor.pedidos) &&
    eNumero(valor.receita)
  );
}

export function eEvolucaoDeVendas(valor: unknown): valor is EvolucaoDeVendas {
  return (
    eObjeto(valor) &&
    eDatasDoPeriodo(valor.periodo) &&
    eUmDe(AGRUPAMENTOS, valor.agrupamento) &&
    Array.isArray(valor.pontos) &&
    valor.pontos.every(ePonto)
  );
}

/** Nenhum pedido em nenhum ponto: o bloco mostra o estado vazio. */
export function semPedidos(evolucao: EvolucaoDeVendas): boolean {
  return evolucao.pontos.every((ponto) => ponto.pedidos === 0);
}

/** Ano, mês e dia de uma data ISO, sem passar por `Date` e pelo fuso do navegador. */
function partes(iso: string): {
  ano: string;
  mes: string;
  dia: string;
  nomeDoMes: string;
} {
  const [ano = "", mes = "", dia = ""] = iso.split("-");
  return { ano, mes, dia, nomeDoMes: MESES[Number(mes) - 1] ?? mes };
}

/** O rótulo curto do eixo: "02/11" para dia e semana, "dez/25" para mês. */
export function rotuloDoEixo(inicio: string, agrupamento: Agrupamento): string {
  const { ano, mes, dia, nomeDoMes } = partes(inicio);
  if (agrupamento === "mes") return `${nomeDoMes.slice(0, 3)}/${ano.slice(2)}`;
  return `${dia}/${mes}`;
}

/** O ponto por extenso, para a dica: "02/11/2026", "Semana de 31/08/2026", "Dezembro de 2025". */
export function rotuloDoPonto(
  inicio: string,
  agrupamento: Agrupamento,
): string {
  const { ano, mes, dia, nomeDoMes } = partes(inicio);
  const data = `${dia}/${mes}/${ano}`;
  if (agrupamento === "dia") return data;
  if (agrupamento === "semana") return `Semana de ${data}`;
  return `${nomeDoMes.charAt(0).toUpperCase()}${nomeDoMes.slice(1)} de ${ano}`;
}
