/** O contrato de `GET /diretoria/tendencia`: números crus e datas ISO. */

import {
  type DatasDoPeriodo,
  eContagem,
  eDataIso,
  eDatasDoPeriodo,
  eNumero,
  eNumeroOuNulo,
  eObjeto,
  eUmDe,
} from "../painel/contrato";
import { AGRUPAMENTOS, type Agrupamento } from "../vendas/evolucao";

export interface PontoDaTendencia {
  /** O primeiro dia do ponto no calendário (a segunda da semana, o dia 1 do mês). */
  inicio: string;
  /** Pagamentos aprovados dos pedidos do ponto, com frete: a mesma receita de Vendas. */
  receita: number;
  /** Dos clientes com pedido aprovado no ponto, a parte com recompra nele; `null` sem cliente. */
  taxa_de_recompra: number | null;
  clientes: number;
  clientes_com_recompra: number;
  /** A nota média das avaliações do ponto, de 1 a 5; `null` sem avaliação. */
  satisfacao: number | null;
  avaliacoes: number;
  /** Dos pedidos do ponto já entregues, a parte com atraso; `null` sem entregue. */
  taxa_de_atraso: number | null;
  entregues: number;
  atrasos: number;
}

export interface TendenciaDaDiretoria {
  periodo: DatasDoPeriodo;
  /** Dia em 30 dias, semana em 90 dias, mês em 12 e 24 meses, como em Vendas. */
  agrupamento: Agrupamento;
  /** Em ordem, um por dia, semana ou mês do período. */
  pontos: PontoDaTendencia[];
}

const NOTA_MINIMA = 1;
const NOTA_MAXIMA = 5;

/** Uma taxa de 0 a 1 com a parte e o todo contados: vazia só quando o todo é zero. */
function eTaxaContada(taxa: unknown, parte: unknown, todo: unknown): boolean {
  if (!eContagem(parte) || !eContagem(todo) || parte > todo) return false;
  if (todo === 0) return taxa === null;
  return eNumero(taxa) && taxa >= 0 && taxa <= 1;
}

function eSatisfacao(nota: unknown, avaliacoes: unknown): boolean {
  if (!eContagem(avaliacoes) || !eNumeroOuNulo(nota)) return false;
  if (avaliacoes === 0) return nota === null;
  return nota !== null && nota >= NOTA_MINIMA && nota <= NOTA_MAXIMA;
}

function ePonto(valor: unknown): valor is PontoDaTendencia {
  return (
    eObjeto(valor) &&
    eDataIso(valor.inicio) &&
    eNumero(valor.receita) &&
    valor.receita >= 0 &&
    eTaxaContada(valor.taxa_de_recompra, valor.clientes_com_recompra, valor.clientes) &&
    eSatisfacao(valor.satisfacao, valor.avaliacoes) &&
    eTaxaContada(valor.taxa_de_atraso, valor.atrasos, valor.entregues)
  );
}

export function eTendenciaDaDiretoria(valor: unknown): valor is TendenciaDaDiretoria {
  return (
    eObjeto(valor) &&
    eDatasDoPeriodo(valor.periodo) &&
    eUmDe(AGRUPAMENTOS, valor.agrupamento) &&
    Array.isArray(valor.pontos) &&
    valor.pontos.every(ePonto)
  );
}

/** Nenhum cliente com pedido aprovado em nenhum ponto: o bloco mostra o estado vazio. */
export function semClientes(tendencia: TendenciaDaDiretoria): boolean {
  return tendencia.pontos.every((ponto) => ponto.clientes === 0);
}
