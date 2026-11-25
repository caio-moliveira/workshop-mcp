/** O contrato de `GET /produtos/notas`: números crus e datas ISO. */

import { type DatasDoPeriodo, eDatasDoPeriodo, eObjeto } from "../painel/contrato";

/** As notas de uma avaliação, de 1 a 5, na ordem em que a API as devolve. */
export const NOTAS = [1, 2, 3, 4, 5] as const;

export type Nota = (typeof NOTAS)[number];

export interface AvaliacoesNaNota {
  nota: Nota;
  avaliacoes: number;
}

export interface NotasDasAvaliacoes {
  periodo: DatasDoPeriodo;
  /** Sempre as cinco notas, de 1 a 5, com zero onde não há avaliação. */
  notas: AvaliacoesNaNota[];
}

function eContagem(valor: unknown): valor is number {
  return Number.isInteger(valor) && (valor as number) >= 0;
}

export function eNotasDasAvaliacoes(valor: unknown): valor is NotasDasAvaliacoes {
  if (!eObjeto(valor)) return false;
  const { notas } = valor;
  return (
    eDatasDoPeriodo(valor.periodo) &&
    Array.isArray(notas) &&
    notas.length === NOTAS.length &&
    notas.every(
      (item: unknown, i) => eObjeto(item) && item.nota === NOTAS[i] && eContagem(item.avaliacoes),
    )
  );
}

/** Nenhuma avaliação do período em nenhuma nota: o bloco mostra o estado vazio. */
export function semAvaliacoes(dados: NotasDasAvaliacoes): boolean {
  return dados.notas.every((item) => item.avaliacoes === 0);
}
