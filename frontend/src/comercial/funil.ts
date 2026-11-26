/** O contrato de `GET /comercial/funil`: números crus e datas ISO. */

import { type DatasDoPeriodo, eDatasDoPeriodo, eObjeto } from "../painel/contrato";
import { ETAPAS, type Etapa } from "./etapas";

export interface LeadsNaEtapa {
  etapa: Etapa;
  /** Os leads criados no período que estão hoje nesta etapa. */
  leads: number;
}

export interface FunilDoComercial {
  periodo: DatasDoPeriodo;
  /** Sempre as seis etapas, na ordem do funil e com Perdido por último, com zero onde não há lead. */
  etapas: LeadsNaEtapa[];
}

function eContagem(valor: unknown): valor is number {
  return Number.isInteger(valor) && (valor as number) >= 0;
}

export function eFunilDoComercial(valor: unknown): valor is FunilDoComercial {
  if (!eObjeto(valor)) return false;
  const { etapas } = valor;
  return (
    eDatasDoPeriodo(valor.periodo) &&
    Array.isArray(etapas) &&
    etapas.length === ETAPAS.length &&
    etapas.every(
      (item: unknown, i) => eObjeto(item) && item.etapa === ETAPAS[i] && eContagem(item.leads),
    )
  );
}

/** Nenhum lead criado no período em nenhuma etapa: o bloco mostra o estado vazio. */
export function semLeads(dados: FunilDoComercial): boolean {
  return dados.etapas.every((item) => item.leads === 0);
}
