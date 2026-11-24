import { describe, expect, it } from "vitest";

import { eEvolucaoDeVendas, rotuloDoEixo, rotuloDoIntervalo, semPedidos } from "./evolucao";

/** Uma resposta de `GET /vendas/evolucao?periodo=90d`, como a API a devolve. */
function resposta(): Record<string, unknown> {
  return {
    agrupamento: "semana",
    pontos: [
      { inicio: "2026-08-31", pedidos: 412, receita: 98765.43 },
      { inicio: "2026-09-07", pedidos: 0, receita: 0 },
    ],
  };
}

/** Uma resposta de um ponto só, com os campos dados trocados. */
function comPonto(troca: Record<string, unknown>): Record<string, unknown> {
  return { agrupamento: "dia", pontos: [{ inicio: "2026-08-31", pedidos: 1, receita: 1, ...troca }] };
}

describe("validação da resposta de evolução", () => {
  it("aceita a resposta do contrato", () => {
    expect(eEvolucaoDeVendas(resposta())).toBe(true);
  });

  it.each(["dia", "semana", "mes"])("aceita o agrupamento %s", (agrupamento) => {
    expect(eEvolucaoDeVendas({ ...resposta(), agrupamento })).toBe(true);
  });

  it("aceita a lista vazia de pontos", () => {
    expect(eEvolucaoDeVendas({ agrupamento: "dia", pontos: [] })).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["agrupamento desconhecido", { ...resposta(), agrupamento: "ano" }],
    ["sem pontos", { agrupamento: "dia" }],
    ["pontos como objeto", { agrupamento: "dia", pontos: {} }],
    ["data fora do ISO", comPonto({ inicio: "31/08/2026" })],
    ["pedidos como texto", comPonto({ pedidos: "1" })],
    ["pedidos fracionário", comPonto({ pedidos: 1.5 })],
    ["receita ausente", comPonto({ receita: undefined })],
    ["receita NaN", comPonto({ receita: Number.NaN })],
    ["ponto nulo", { agrupamento: "dia", pontos: [null] }],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eEvolucaoDeVendas(corpo)).toBe(false);
  });
});

describe("rótulos dos intervalos", () => {
  it("no eixo, dia e semana como dia/mês, mês abreviado com o ano", () => {
    expect(rotuloDoEixo("2026-11-02", "dia")).toBe("02/11");
    expect(rotuloDoEixo("2026-08-31", "semana")).toBe("31/08");
    expect(rotuloDoEixo("2025-12-01", "mes")).toBe("dez/25");
    expect(rotuloDoEixo("2026-01-01", "mes")).toBe("jan/26");
  });

  it("na dica, o intervalo por extenso", () => {
    expect(rotuloDoIntervalo("2026-11-02", "dia")).toBe("02/11/2026");
    expect(rotuloDoIntervalo("2026-08-31", "semana")).toBe("Semana de 31/08/2026");
    expect(rotuloDoIntervalo("2025-12-01", "mes")).toBe("Dezembro de 2025");
  });

  it("não desloca o dia pelo fuso do navegador", () => {
    expect(rotuloDoEixo("2026-03-01", "mes")).toBe("mar/26");
    expect(rotuloDoEixo("2026-03-01", "dia")).toBe("01/03");
  });
});

describe("evolução sem pedidos", () => {
  it("vazia quando nenhum ponto tem pedido", () => {
    const zerado = { inicio: "2026-11-01", pedidos: 0, receita: 0 };
    expect(semPedidos({ agrupamento: "dia", pontos: [] })).toBe(true);
    expect(semPedidos({ agrupamento: "dia", pontos: [zerado] })).toBe(true);
  });

  it("com dados quando algum ponto tem pedido", () => {
    const zerado = { inicio: "2026-11-01", pedidos: 0, receita: 0 };
    const comPedido = { inicio: "2026-11-02", pedidos: 1, receita: 0 };
    expect(semPedidos({ agrupamento: "dia", pontos: [zerado, comPedido] })).toBe(false);
  });
});
