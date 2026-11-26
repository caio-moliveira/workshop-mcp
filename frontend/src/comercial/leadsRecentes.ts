/** O contrato de `GET /comercial/leads`: os leads mais recentes do período. */

import {
  type DatasDoPeriodo,
  eDataIso,
  eDatasDoPeriodo,
  eObjeto,
  eTexto,
  eUmDe,
} from "../painel/contrato";
import { CANAIS, type Canal } from "./canais";
import { ETAPAS, FECHADO, type Etapa } from "./etapas";

export const LIMITE_DE_LEADS_RECENTES = 20;

export interface LeadRecente {
  /** O identificador do lead. */
  lead: number;
  /** O nome da empresa: texto gerado, não escrito por clientes. */
  empresa: string;
  canal: Canal;
  /** A etapa atual do funil. */
  etapa: Etapa;
  /** A data ISO em que o lead entrou no funil. */
  data_criacao: string;
  /** A data ISO em que o lead virou lojista; `null` em quem não fechou. */
  data_fechamento: string | null;
}

export interface LeadsRecentes {
  periodo: DatasDoPeriodo;
  /** Do mais recente para o mais antigo pela data de criação, no máximo 20. */
  leads: LeadRecente[];
}

/** Só o lead na etapa Fechado tem data de fechamento, e ele sempre a tem. */
function eFechamentoDaEtapa(etapa: Etapa, fechamento: unknown): boolean {
  return etapa === FECHADO ? eDataIso(fechamento) : fechamento === null;
}

function eLeadRecente(valor: unknown): valor is LeadRecente {
  if (!eObjeto(valor)) return false;
  const { etapa } = valor;
  return (
    Number.isInteger(valor.lead) &&
    eTexto(valor.empresa) &&
    eUmDe(CANAIS, valor.canal) &&
    eUmDe(ETAPAS, etapa) &&
    eDataIso(valor.data_criacao) &&
    eFechamentoDaEtapa(etapa, valor.data_fechamento)
  );
}

export function eLeadsRecentes(valor: unknown): valor is LeadsRecentes {
  if (!eObjeto(valor)) return false;
  const { leads } = valor;
  return (
    eDatasDoPeriodo(valor.periodo) &&
    Array.isArray(leads) &&
    leads.length <= LIMITE_DE_LEADS_RECENTES &&
    leads.every(eLeadRecente)
  );
}
