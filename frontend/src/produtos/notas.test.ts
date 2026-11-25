import { describe, expect, it } from "vitest";

import { eNotasDasAvaliacoes, NOTAS, semAvaliacoes } from "./notas";

/** Uma resposta de `GET /produtos/notas?periodo=24m`, como a API a devolve. */
function resposta(): Record<string, unknown> {
  return {
    periodo: { inicio: "2024-12-01", fim: "2026-11-30" },
    notas: [
      { nota: 1, avaliacoes: 1382 },
      { nota: 2, avaliacoes: 1169 },
      { nota: 3, avaliacoes: 1988 },
      { nota: 4, avaliacoes: 5329 },
      { nota: 5, avaliacoes: 10246 },
    ],
  };
}

/** A resposta com o item da posição dada trocado. */
function comNota(posicao: number, troca: unknown): Record<string, unknown> {
  const notas = [...(resposta().notas as unknown[])];
  notas[posicao] = troca;
  return { ...resposta(), notas };
}

describe("validação da resposta de avaliações por nota", () => {
  it("aceita a resposta do contrato", () => {
    expect(eNotasDasAvaliacoes(resposta())).toBe(true);
  });

  it("aceita zero numa nota sem avaliação no período", () => {
    expect(eNotasDasAvaliacoes(comNota(0, { nota: 1, avaliacoes: 0 }))).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem período", { notas: resposta().notas }],
    ["período fora do ISO", { ...resposta(), periodo: { inicio: "01/12/2024", fim: "2026-11-30" } }],
    ["sem notas", { periodo: resposta().periodo }],
    ["notas como objeto", { ...resposta(), notas: {} }],
    ["só quatro notas", { ...resposta(), notas: (resposta().notas as unknown[]).slice(1) }],
    ["notas fora de ordem", { ...resposta(), notas: [...(resposta().notas as unknown[])].reverse() }],
    ["nota fora da escala", comNota(4, { nota: 6, avaliacoes: 1 })],
    ["avaliações como texto", comNota(1, { nota: 2, avaliacoes: "1169" })],
    ["avaliações fracionárias", comNota(1, { nota: 2, avaliacoes: 1.5 })],
    ["avaliações negativas", comNota(1, { nota: 2, avaliacoes: -1 })],
    ["item nulo", comNota(2, null)],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eNotasDasAvaliacoes(corpo)).toBe(false);
  });
});

describe("avaliações por nota sem avaliações", () => {
  const periodo = { inicio: "2026-11-01", fim: "2026-11-30" };

  it("é vazio quando as cinco notas têm zero", () => {
    const notas = NOTAS.map((nota) => ({ nota, avaliacoes: 0 }));

    expect(semAvaliacoes({ periodo, notas })).toBe(true);
  });

  it("não é vazio com uma avaliação em qualquer nota", () => {
    const notas = NOTAS.map((nota) => ({ nota, avaliacoes: nota === 3 ? 1 : 0 }));

    expect(semAvaliacoes({ periodo, notas })).toBe(false);
  });
});
