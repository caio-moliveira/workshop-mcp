import { describe, expect, it } from "vitest";

import { eSituacaoDasEntregas, semEntregas } from "./situacaoDasEntregas";

/** Uma resposta de `GET /vendas/situacao-das-entregas`, como a API a devolve. */
function resposta(): Record<string, unknown> {
  return {
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    situacoes: [
      { situacao: "Em trânsito", pedidos: 1204 },
      { situacao: "Prazo vencido", pedidos: 87 },
      { situacao: "Entregue no prazo", pedidos: 15890 },
      { situacao: "Entregue com atraso", pedidos: 0 },
    ],
  };
}

/** A resposta com a situação da posição dada trocada. */
function comSituacao(posicao: number, troca: unknown): Record<string, unknown> {
  const situacoes = [...(resposta().situacoes as unknown[])];
  situacoes[posicao] = troca;
  return { ...resposta(), situacoes };
}

describe("validação da resposta de situação das entregas", () => {
  it("aceita a resposta do contrato, com zero numa situação", () => {
    expect(eSituacaoDasEntregas(resposta())).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem período", { situacoes: resposta().situacoes }],
    ["período fora do ISO", { ...resposta(), periodo: { inicio: "01/12/2025", fim: "2026-11-30" } }],
    ["sem situações", { periodo: resposta().periodo }],
    ["situações como objeto", { ...resposta(), situacoes: {} }],
    ["só três situações", { ...resposta(), situacoes: (resposta().situacoes as unknown[]).slice(1) }],
    [
      "situações fora de ordem",
      { ...resposta(), situacoes: [...(resposta().situacoes as unknown[])].reverse() },
    ],
    ["situação desconhecida", comSituacao(0, { situacao: "Extraviado", pedidos: 1 })],
    ["pedidos como texto", comSituacao(1, { situacao: "Prazo vencido", pedidos: "87" })],
    ["pedidos fracionário", comSituacao(1, { situacao: "Prazo vencido", pedidos: 1.5 })],
    ["pedidos negativo", comSituacao(1, { situacao: "Prazo vencido", pedidos: -1 })],
    ["situação nula", comSituacao(2, null)],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eSituacaoDasEntregas(corpo)).toBe(false);
  });
});

describe("situação das entregas sem entregas", () => {
  const periodo = { inicio: "2026-11-01", fim: "2026-11-30" };
  const com = (...pedidos: number[]) => ({
    periodo,
    situacoes: (
      ["Em trânsito", "Prazo vencido", "Entregue no prazo", "Entregue com atraso"] as const
    ).map((situacao, i) => ({ situacao, pedidos: pedidos[i] ?? 0 })),
  });

  it("vazia quando as quatro situações estão zeradas", () => {
    expect(semEntregas(com(0, 0, 0, 0))).toBe(true);
  });

  it("com dados quando alguma situação tem pedido", () => {
    expect(semEntregas(com(0, 0, 0, 3))).toBe(false);
  });
});
