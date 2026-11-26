/** O contrato de `GET /produtos/categorias`: números crus e datas ISO. */

import {
  type DatasDoPeriodo,
  eContagem,
  eDatasDoPeriodo,
  eNumero,
  eObjeto,
} from "../painel/contrato";

export interface CategoriaDeProdutos {
  categoria: string;
  /** Produtos do catálogo na categoria: não depende do período. */
  produtos: number;
  avaliacoes: number;
  /** De 1 a 5; `null` quando a categoria não tem avaliação no período. */
  nota_media: number | null;
  /** Avaliações com nota 1 ou 2. */
  reclamacoes: number;
  /** Reclamações ÷ avaliações, de 0 a 1; `null` quando a categoria não tem avaliação no período. */
  taxa_de_reclamacao: number | null;
}

export interface CategoriasDeProdutos {
  periodo: DatasDoPeriodo;
  /** Todas as categorias, da pior nota média para a melhor. */
  categorias: CategoriaDeProdutos[];
}

/** Quantas categorias o gráfico de reclamações mostra (FE §6). */
export const CATEGORIAS_NO_GRAFICO = 8;

function eNaFaixa(valor: unknown, minimo: number, maximo: number): boolean {
  return eNumero(valor) && valor >= minimo && valor <= maximo;
}

function eCategoria(valor: unknown): valor is CategoriaDeProdutos {
  if (!eObjeto(valor)) return false;
  const { avaliacoes, nota_media: nota, taxa_de_reclamacao: taxa } = valor;
  if (!(eContagem(avaliacoes) && eContagem(valor.produtos) && eContagem(valor.reclamacoes))) {
    return false;
  }
  const medidasValidas =
    avaliacoes === 0
      ? nota === null && taxa === null
      : eNaFaixa(nota, 1, 5) && eNaFaixa(taxa, 0, 1);
  return typeof valor.categoria === "string" && valor.categoria !== "" && medidasValidas;
}

export function eCategoriasDeProdutos(valor: unknown): valor is CategoriasDeProdutos {
  return (
    eObjeto(valor) &&
    eDatasDoPeriodo(valor.periodo) &&
    Array.isArray(valor.categorias) &&
    valor.categorias.every(eCategoria)
  );
}

/**
 * As categorias com mais reclamações no período, da maior para a menor, até
 * `CATEGORIAS_NO_GRAFICO`. No empate, a ordem é a do nome. Sem reclamação, a categoria fica de
 * fora; num período sem nenhuma, a lista é vazia e o bloco mostra o estado vazio.
 */
export function categoriasComMaisReclamacoes(dados: CategoriasDeProdutos): CategoriaDeProdutos[] {
  return dados.categorias
    .filter((item) => item.reclamacoes > 0)
    .sort(
      (a, b) => b.reclamacoes - a.reclamacoes || a.categoria.localeCompare(b.categoria, "pt-BR"),
    )
    .slice(0, CATEGORIAS_NO_GRAFICO);
}
