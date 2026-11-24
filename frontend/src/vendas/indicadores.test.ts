import { describe, expect, it } from "vitest";

import { eIndicadoresDeVendas } from "./indicadores";

/** Uma resposta de `GET /vendas/indicadores?periodo=12m`, como a API a devolve. */
function resposta(): Record<string, unknown> {
  return {
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    pedidos_realizados: { atual: 17480, anterior: 12520 },
    receita: { atual: 4321987.65, anterior: 3012345.1 },
    taxa_de_atraso: { atual: 0.1012, anterior: 0.0987, atrasos: 1500 },
    taxa_de_aprovacao: { atual: 0.9, anterior: 0.89 },
  };
}

describe("validação da resposta de indicadores", () => {
  it("aceita a resposta do contrato", () => {
    expect(eIndicadoresDeVendas(resposta())).toBe(true);
  });

  it("aceita o anterior nulo (24 meses) e taxa nula sem denominador", () => {
    const corpo = resposta();
    corpo.pedidos_realizados = { atual: 0, anterior: null };
    corpo.receita = { atual: 0, anterior: null };
    corpo.taxa_de_atraso = { atual: null, anterior: null, atrasos: 0 };
    corpo.taxa_de_aprovacao = { atual: null, anterior: null };

    expect(eIndicadoresDeVendas(corpo)).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem receita", { ...resposta(), receita: undefined }],
    ["número como texto", { ...resposta(), pedidos_realizados: { atual: "10", anterior: 1 } }],
    ["anterior ausente", { ...resposta(), taxa_de_aprovacao: { atual: 0.9 } }],
    ["sem a contagem de atrasos", { ...resposta(), taxa_de_atraso: { atual: 0.1, anterior: 0.1 } }],
    ["data fora do ISO", { ...resposta(), periodo: { inicio: "01/12/2025", fim: "2026-11-30" } }],
    ["NaN", { ...resposta(), receita: { atual: Number.NaN, anterior: null } }],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eIndicadoresDeVendas(corpo)).toBe(false);
  });
});
