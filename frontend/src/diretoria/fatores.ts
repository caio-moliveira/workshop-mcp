/** O contrato de `GET /diretoria/fatores-de-recompra`: números crus e datas ISO. */

import {
  type DatasDoPeriodo,
  eDatasDoPeriodo,
  eObjeto,
  eSatisfacaoContada,
  eTaxaContada,
} from "../painel/contrato";

/** Os grupos de cada bloco, na ordem em que a resposta os traz. Os grupos sem desfecho não vêm. */
export const GRUPOS_DA_PRIMEIRA_ENTREGA = ["No prazo", "Com atraso"] as const;
export const GRUPOS_DA_PRIMEIRA_NOTA = ["1 ou 2", "3", "4 ou 5"] as const;
export const FAIXAS_DE_ATRASO = ["No prazo", "Até 7 dias", "Mais de 7 dias"] as const;

/** Um grupo de clientes pelo primeiro pedido aprovado deles, qualquer que seja a data dele. */
export interface GrupoDeRecompra<G extends string = string> {
  grupo: G;
  /** Os clientes com pedido aprovado no período cujo primeiro pedido caiu no grupo. */
  clientes: number;
  /** Os que deles fizeram uma recompra no período. */
  clientes_com_recompra: number;
  /** Clientes com recompra ÷ clientes, de 0 a 1; `null` no grupo sem clientes. */
  taxa_de_recompra: number | null;
}

/** As avaliações do período cujo pedido foi entregue na faixa de atraso. */
export interface GrupoDeSatisfacao {
  grupo: (typeof FAIXAS_DE_ATRASO)[number];
  avaliacoes: number;
  /** A nota média delas, de 1 a 5; `null` na faixa sem avaliações. */
  satisfacao: number | null;
}

export interface FatoresDeRecompra {
  periodo: DatasDoPeriodo;
  /** A recompra pela entrega do primeiro pedido; em trânsito e prazo vencido ficam de fora. */
  primeira_entrega: GrupoDeRecompra<(typeof GRUPOS_DA_PRIMEIRA_ENTREGA)[number]>[];
  /** A recompra pela nota do primeiro pedido; quem não o avaliou fica de fora. */
  primeira_nota: GrupoDeRecompra<(typeof GRUPOS_DA_PRIMEIRA_NOTA)[number]>[];
  /** A satisfação das avaliações do período pela faixa de atraso da entrega. */
  faixa_de_atraso: GrupoDeSatisfacao[];
}

function eGrupoDeRecompra(valor: unknown): boolean {
  return (
    eObjeto(valor) &&
    eTaxaContada(valor.taxa_de_recompra, valor.clientes_com_recompra, valor.clientes)
  );
}

function eGrupoDeSatisfacao(valor: unknown): boolean {
  return eObjeto(valor) && eSatisfacaoContada(valor.satisfacao, valor.avaliacoes);
}

/** O bloco traz exatamente os grupos dele, cada um uma vez e na ordem, e todos válidos. */
function eBloco(
  valor: unknown,
  grupos: readonly string[],
  eGrupo: (grupo: unknown) => boolean,
): boolean {
  return (
    Array.isArray(valor) &&
    valor.length === grupos.length &&
    valor.every(
      (item: unknown, i) => eGrupo(item) && (item as { grupo: unknown }).grupo === grupos[i],
    )
  );
}

export function eFatoresDeRecompra(valor: unknown): valor is FatoresDeRecompra {
  return (
    eObjeto(valor) &&
    eDatasDoPeriodo(valor.periodo) &&
    eBloco(valor.primeira_entrega, GRUPOS_DA_PRIMEIRA_ENTREGA, eGrupoDeRecompra) &&
    eBloco(valor.primeira_nota, GRUPOS_DA_PRIMEIRA_NOTA, eGrupoDeRecompra) &&
    eBloco(valor.faixa_de_atraso, FAIXAS_DE_ATRASO, eGrupoDeSatisfacao)
  );
}

/** Nenhum cliente e nenhuma avaliação em nenhum grupo: não há o que mostrar. */
export function semGrupos(fatores: FatoresDeRecompra): boolean {
  return (
    [...fatores.primeira_entrega, ...fatores.primeira_nota].every((item) => item.clientes === 0) &&
    fatores.faixa_de_atraso.every((item) => item.avaliacoes === 0)
  );
}
