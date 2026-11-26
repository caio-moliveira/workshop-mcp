/** O contrato de `GET /diretoria/resumo`: números crus e datas ISO. */

import { CANAIS, type Canal } from "../comercial/canais";
import {
  type DatasDoPeriodo,
  eContagem,
  eDatasDoPeriodo,
  eNumero,
  eObjeto,
  eUmDe,
} from "../painel/contrato";

/**
 * Um canal do lojista (o do lead que originou o lojista) no período. Pedidos, receita e taxa de
 * atraso são dos pedidos dos lojistas do canal, com as regras de Vendas; a satisfação, das
 * avaliações desses pedidos; na taxa de recompra, o cliente conta no canal do lojista do primeiro
 * pedido dele.
 */
export interface ResumoDoCanal {
  canal: Canal;
  pedidos: number;
  /** Pagamentos aprovados dos pedidos do canal, com frete. */
  receita: number;
  /** Atrasos ÷ entregues, de 0 a 1; `null` no canal sem pedido entregue no período. */
  taxa_de_atraso: number | null;
  entregues: number;
  atrasos: number;
  /** A nota média, de 1 a 5; `null` no canal sem avaliação no período. */
  satisfacao: number | null;
  avaliacoes: number;
  /** Clientes com recompra ÷ clientes, de 0 a 1; `null` no canal sem cliente no período. */
  taxa_de_recompra: number | null;
  clientes: number;
  clientes_com_recompra: number;
}

export interface ResumoPorCanal {
  periodo: DatasDoPeriodo;
  /** Os cinco canais, da maior taxa de atraso para a menor; os de taxa vazia, no fim. */
  canais: ResumoDoCanal[];
}

const NOTA_MINIMA = 1;
const NOTA_MAXIMA = 5;

function eFracao(valor: unknown): boolean {
  return eNumero(valor) && valor >= 0 && valor <= 1;
}

/** Uma taxa com a parte e o todo contados: vazia exatamente quando o todo é zero. */
function eTaxaContada(taxa: unknown, parte: unknown, todo: unknown): boolean {
  return (
    eContagem(parte) &&
    eContagem(todo) &&
    parte <= todo &&
    (todo === 0 ? taxa === null : eFracao(taxa))
  );
}

function eSatisfacao(satisfacao: unknown, avaliacoes: unknown): boolean {
  if (!eContagem(avaliacoes)) return false;
  if (avaliacoes === 0) return satisfacao === null;
  return eNumero(satisfacao) && satisfacao >= NOTA_MINIMA && satisfacao <= NOTA_MAXIMA;
}

function eResumoDoCanal(valor: unknown): valor is ResumoDoCanal {
  return (
    eObjeto(valor) &&
    eUmDe(CANAIS, valor.canal) &&
    eContagem(valor.pedidos) &&
    eNumero(valor.receita) &&
    valor.receita >= 0 &&
    eTaxaContada(valor.taxa_de_atraso, valor.atrasos, valor.entregues) &&
    eSatisfacao(valor.satisfacao, valor.avaliacoes) &&
    eTaxaContada(valor.taxa_de_recompra, valor.clientes_com_recompra, valor.clientes)
  );
}

export function eResumoPorCanal(valor: unknown): valor is ResumoPorCanal {
  if (!eObjeto(valor) || !eDatasDoPeriodo(valor.periodo) || !Array.isArray(valor.canais)) {
    return false;
  }
  const canais: unknown[] = valor.canais;
  // Sempre os cinco canais, cada um uma vez.
  return (
    canais.length === CANAIS.length &&
    canais.every(eResumoDoCanal) &&
    new Set(canais.map((item) => item.canal)).size === CANAIS.length
  );
}

/** Nenhum pedido no período, em nenhum canal: não há o que mostrar. */
export function semPedidos(canais: ResumoDoCanal[]): boolean {
  return canais.every((item) => item.pedidos === 0);
}
