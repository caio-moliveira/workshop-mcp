import { describe, expect, it } from "vitest";

import { categoriasComMaisReclamacoes, eCategoriasDeProdutos } from "./categorias";

function categoria(nome: string, reclamacoes: number, avaliacoes = 1000, nota = 4.1) {
  return {
    categoria: nome,
    produtos: 100,
    avaliacoes,
    nota_media: avaliacoes === 0 ? null : nota,
    reclamacoes,
    taxa_de_reclamacao: avaliacoes === 0 ? null : reclamacoes / avaliacoes,
  };
}

/** Uma resposta de `GET /produtos/categorias`, como a API a devolve (encurtada). */
function resposta(): Record<string, unknown> {
  return {
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    categorias: [
      categoria("Eletrônicos", 341, 2400, 3.92),
      categoria("Brinquedos", 24, 300, 4.27),
      categoria("Livros", 0, 0),
    ],
  };
}

function comCategoria(troca: unknown): Record<string, unknown> {
  return { ...resposta(), categorias: [troca, ...(resposta().categorias as unknown[]).slice(1)] };
}

describe("validação da resposta de categorias de Produtos", () => {
  it("aceita a resposta do contrato, com uma categoria sem avaliação no período", () => {
    expect(eCategoriasDeProdutos(resposta())).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem período", { categorias: resposta().categorias }],
    ["sem categorias", { periodo: resposta().periodo }],
    ["categorias como objeto", { ...resposta(), categorias: {} }],
    ["item nulo", comCategoria(null)],
    ["nome vazio", comCategoria({ ...categoria("", 1), categoria: "" })],
    ["nome como número", comCategoria({ ...categoria("X", 1), categoria: 7 })],
    ["reclamações como texto", comCategoria({ ...categoria("X", 1), reclamacoes: "1" })],
    ["avaliações fracionárias", comCategoria({ ...categoria("X", 1), avaliacoes: 1.5 })],
    ["produtos negativos", comCategoria({ ...categoria("X", 1), produtos: -1 })],
    ["sem taxa", comCategoria({ ...categoria("X", 1), taxa_de_reclamacao: undefined })],
    ["taxa acima de 1", comCategoria({ ...categoria("X", 1), taxa_de_reclamacao: 1.2 })],
    ["nota fora da escala", comCategoria({ ...categoria("X", 1), nota_media: 5.5 })],
    ["nota nula com avaliações", comCategoria({ ...categoria("X", 1), nota_media: null })],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eCategoriasDeProdutos(corpo)).toBe(false);
  });
});

describe("as categorias com mais reclamações", () => {
  const periodo = { inicio: "2025-12-01", fim: "2026-11-30" };

  it("traz as 8 com mais reclamações, da maior para a menor", () => {
    const categorias = [5, 90, 12, 300, 41, 7, 150, 66, 23, 18].map((n, i) =>
      categoria(`Categoria ${i}`, n),
    );

    const maiores = categoriasComMaisReclamacoes({ periodo, categorias });

    expect(maiores.map((item) => item.reclamacoes)).toEqual([300, 150, 90, 66, 41, 23, 18, 12]);
  });

  it("no empate de reclamações, a ordem é a do nome", () => {
    const categorias = [categoria("Papelaria", 10), categoria("Áudio", 10), categoria("Moda", 10)];

    const maiores = categoriasComMaisReclamacoes({ periodo, categorias });

    expect(maiores.map((item) => item.categoria)).toEqual(["Áudio", "Moda", "Papelaria"]);
  });

  it("deixa de fora as categorias sem reclamação", () => {
    const categorias = [categoria("Livros", 0, 0), categoria("Moda", 0), categoria("Casa", 3)];

    const maiores = categoriasComMaisReclamacoes({ periodo, categorias });

    expect(maiores.map((item) => item.categoria)).toEqual(["Casa"]);
  });

  it("é vazia num período sem reclamação", () => {
    const categorias = [categoria("Livros", 0, 0), categoria("Moda", 0)];

    expect(categoriasComMaisReclamacoes({ periodo, categorias })).toEqual([]);
  });
});
