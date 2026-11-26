/** O contrato de `GET /comercial/canais`: números crus e datas ISO. */

import {
  type DatasDoPeriodo,
  eContagem,
  eDatasDoPeriodo,
  eNumero,
  eObjeto,
  eUmDe,
} from "../painel/contrato";
import type { Periodo } from "../painel/periodo";
import type { EstadoDoBloco } from "../useBloco";
import { CANAIS, type Canal } from "./canais";

export interface DesempenhoDoCanal {
  canal: Canal;
  /** Leads do canal criados no período. */
  leads: number;
  /** Leads do canal que fecharam no período, contados pela data de fechamento. */
  novos_lojistas: number;
  /**
   * Novos lojistas ÷ leads do período, do canal; `null` no canal sem lead criado no período. Não
   * é uma coorte: pode passar de 1 quando leads antigos fecham num período de poucos leads.
   */
  conversao: number | null;
  /** Média de dias da criação ao fechamento; `null` no canal sem fechamento no período. */
  dias_ate_fechar: number | null;
}

export interface DesempenhoDosCanais {
  periodo: DatasDoPeriodo;
  /** Os cinco canais, da maior conversão para a menor; os de conversão vazia, no fim. */
  canais: DesempenhoDoCanal[];
}

/** O caminho da rota dos canais num período: o painel a busca uma vez só. */
export function rotaDosCanais(periodo: Periodo): string {
  return `/comercial/canais?periodo=${periodo}`;
}

/**
 * A busca da rota dos canais, feita uma vez no painel e entregue igual à tabela e ao gráfico: os
 * dois carregam, falham e tentam de novo juntos.
 */
export interface BuscaDosCanais {
  estado: EstadoDoBloco<DesempenhoDosCanais>;
  tentarDeNovo: () => void;
}

function eNaoNegativo(valor: unknown): boolean {
  return eNumero(valor) && valor >= 0;
}

/** A medida é vazia exatamente quando a contagem de que ela depende é zero. */
function eMedidaDe(contagem: number, medida: unknown): boolean {
  return contagem === 0 ? medida === null : eNaoNegativo(medida);
}

function eCanal(valor: unknown): valor is DesempenhoDoCanal {
  if (!eObjeto(valor)) return false;
  const { leads, novos_lojistas: novosLojistas } = valor;
  return (
    eUmDe(CANAIS, valor.canal) &&
    eContagem(leads) &&
    eContagem(novosLojistas) &&
    eMedidaDe(leads, valor.conversao) &&
    eMedidaDe(novosLojistas, valor.dias_ate_fechar)
  );
}

export function eDesempenhoDosCanais(valor: unknown): valor is DesempenhoDosCanais {
  if (!eObjeto(valor) || !eDatasDoPeriodo(valor.periodo) || !Array.isArray(valor.canais)) {
    return false;
  }
  const canais: unknown[] = valor.canais;
  // Sempre os cinco canais, cada um uma vez.
  return (
    canais.length === CANAIS.length &&
    canais.every(eCanal) &&
    new Set(canais.map((item) => item.canal)).size === CANAIS.length
  );
}

/**
 * Os canais para o gráfico de novos lojistas: do canal com mais novos lojistas para o de menos,
 * com o empate pelo nome. A resposta, na ordem da conversão, fica como veio.
 */
export function canaisPorNovosLojistas(canais: DesempenhoDoCanal[]): DesempenhoDoCanal[] {
  return [...canais].sort(
    (a, b) => b.novos_lojistas - a.novos_lojistas || a.canal.localeCompare(b.canal, "pt-BR"),
  );
}
