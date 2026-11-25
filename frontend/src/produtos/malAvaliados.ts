/** O contrato de `GET /produtos/mal-avaliados`: números crus e datas ISO. */

import { type DatasDoPeriodo, eDatasDoPeriodo, eNumero, eObjeto } from "../painel/contrato";

export const LIMITE_DE_MAL_AVALIADOS = 50;

export interface ProdutoMalAvaliado {
  /** O identificador do produto. */
  produto: number;
  nome_do_produto: string;
  categoria: string;
  preco: number;
  /** De 1 a 5, só das avaliações do período; abaixo de 3,0. */
  nota_media: number;
  /** Avaliações do produto no período; pelo menos 3. */
  avaliacoes: number;
}

export interface MalAvaliados {
  periodo: DatasDoPeriodo;
  /** Da pior nota média para a melhor, no máximo 50. */
  produtos: ProdutoMalAvaliado[];
}

function eTexto(valor: unknown): valor is string {
  return typeof valor === "string" && valor !== "";
}

function eProdutoMalAvaliado(valor: unknown): valor is ProdutoMalAvaliado {
  return (
    eObjeto(valor) &&
    Number.isInteger(valor.produto) &&
    eTexto(valor.nome_do_produto) &&
    eTexto(valor.categoria) &&
    eNumero(valor.preco) &&
    eNumero(valor.nota_media) &&
    Number.isInteger(valor.avaliacoes)
  );
}

export function eMalAvaliados(valor: unknown): valor is MalAvaliados {
  if (!eObjeto(valor)) return false;
  const { produtos } = valor;
  return (
    eDatasDoPeriodo(valor.periodo) &&
    Array.isArray(produtos) &&
    produtos.length <= LIMITE_DE_MAL_AVALIADOS &&
    produtos.every(eProdutoMalAvaliado)
  );
}
