import { describe, expect, it } from "vitest";

import { eIndicadoresDaDiretoria } from "./indicadores";

/** Uma resposta de `GET /diretoria/indicadores?periodo=30d`, como a API a devolve. */
function trintaDias(): Record<string, unknown> {
  return {
    periodo: { inicio: "2026-11-01", fim: "2026-11-30" },
    receita: { atual: 2405996.39, anterior: 1347654.75 },
    taxa_de_recompra: {
      atual: 308 / 2173,
      anterior: 167 / 1296,
      clientes_com_recompra: 308,
      clientes: 2173,
    },
    satisfacao: { atual: 4.1229, anterior: 4.0698, avaliacoes: 1237 },
    retencao: {
      atual: 11 / 1296,
      anterior: 9 / 1285,
      retidos: 11,
      clientes_do_periodo_anterior: 1296,
    },
  };
}

/** Em 12 meses, a retenção tem valor e não tem anterior: precisaria de dois períodos para trás. */
function dozeMeses(): Record<string, unknown> {
  return {
    ...trintaDias(),
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    retencao: { atual: 573 / 12495, anterior: null, retidos: 573, clientes_do_periodo_anterior: 12495 },
  };
}

/** Em 24 meses, nenhum indicador tem anterior, e a retenção vem vazia. */
function vinteEQuatroMeses(): Record<string, unknown> {
  return {
    periodo: { inicio: "2024-12-01", fim: "2026-11-30" },
    receita: { atual: 30625969.36, anterior: null },
    taxa_de_recompra: { atual: 1365 / 27301, anterior: null, clientes_com_recompra: 1365, clientes: 27301 },
    satisfacao: { atual: 4.0882, anterior: null, avaliacoes: 20114 },
    retencao: { atual: null, anterior: null, retidos: null, clientes_do_periodo_anterior: null },
  };
}

describe("validação da resposta de indicadores da Diretoria", () => {
  it("aceita a resposta do contrato, com todos os anteriores (30 e 90 dias)", () => {
    expect(eIndicadoresDaDiretoria(trintaDias())).toBe(true);
  });

  it("aceita a retenção sem anterior (12 meses)", () => {
    expect(eIndicadoresDaDiretoria(dozeMeses())).toBe(true);
  });

  it("aceita a retenção vazia e todas as variações vazias (24 meses)", () => {
    expect(eIndicadoresDaDiretoria(vinteEQuatroMeses())).toBe(true);
  });

  it("aceita o período sem avaliações: satisfação vazia", () => {
    const corpo = trintaDias();
    corpo.satisfacao = { atual: null, anterior: 4.07, avaliacoes: 0 };

    expect(eIndicadoresDaDiretoria(corpo)).toBe(true);
  });

  it("aceita o período sem cliente: taxa de recompra vazia e receita zero", () => {
    const corpo = trintaDias();
    corpo.receita = { atual: 0, anterior: 1347654.75 };
    corpo.taxa_de_recompra = { atual: null, anterior: 0.12, clientes_com_recompra: 0, clientes: 0 };
    corpo.retencao = { atual: 0, anterior: 9 / 1285, retidos: 0, clientes_do_periodo_anterior: 1296 };

    expect(eIndicadoresDaDiretoria(corpo)).toBe(true);
  });

  const retencaoDe = (retencao: unknown) => ({ ...trintaDias(), retencao });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem receita", { ...trintaDias(), receita: undefined }],
    ["receita nula", { ...trintaDias(), receita: { atual: null, anterior: null } }],
    ["número como texto", { ...trintaDias(), receita: { atual: "2405996.39", anterior: null } }],
    ["NaN", { ...trintaDias(), receita: { atual: Number.NaN, anterior: null } }],
    ["anterior ausente", { ...trintaDias(), receita: { atual: 1 } }],
    [
      "recompra sem a contagem",
      { ...trintaDias(), taxa_de_recompra: { atual: 0.14, anterior: 0.12, clientes: 2173 } },
    ],
    [
      "mais clientes com recompra do que clientes",
      {
        ...trintaDias(),
        taxa_de_recompra: { atual: 1.5, anterior: 0.12, clientes_com_recompra: 3, clientes: 2 },
      },
    ],
    [
      "contagem com casa decimal",
      {
        ...trintaDias(),
        taxa_de_recompra: { atual: 0.14, anterior: 0.12, clientes_com_recompra: 30.5, clientes: 217 },
      },
    ],
    [
      "taxa de recompra vazia com clientes",
      { ...trintaDias(), taxa_de_recompra: { atual: null, anterior: 0.12, clientes_com_recompra: 3, clientes: 20 } },
    ],
    [
      "taxa de recompra acima de 1",
      { ...trintaDias(), taxa_de_recompra: { atual: 1.5, anterior: 0.12, clientes_com_recompra: 3, clientes: 20 } },
    ],
    [
      "taxa de recompra negativa",
      { ...trintaDias(), taxa_de_recompra: { atual: -0.1, anterior: 0.12, clientes_com_recompra: 3, clientes: 20 } },
    ],
    [
      "retenção acima de 1",
      retencaoDe({ atual: 2, anterior: null, retidos: 11, clientes_do_periodo_anterior: 1296 }),
    ],
    ["satisfação sem a contagem", { ...trintaDias(), satisfacao: { atual: 4.1, anterior: 4.0 } }],
    ["satisfação fora da nota", { ...trintaDias(), satisfacao: { atual: 6, anterior: 4.0, avaliacoes: 10 } }],
    ["satisfação vazia com avaliações", { ...trintaDias(), satisfacao: { atual: null, anterior: 4.0, avaliacoes: 10 } }],
    ["retenção sem os retidos", retencaoDe({ atual: 0.01, anterior: null, clientes_do_periodo_anterior: 1296 })],
    [
      "retenção vazia com clientes do anterior",
      retencaoDe({ atual: null, anterior: null, retidos: null, clientes_do_periodo_anterior: 1296 }),
    ],
    [
      "retenção com valor sem clientes do anterior",
      retencaoDe({ atual: 0.01, anterior: null, retidos: 11, clientes_do_periodo_anterior: null }),
    ],
    [
      "retenção vazia com anterior",
      retencaoDe({ atual: null, anterior: 0.01, retidos: null, clientes_do_periodo_anterior: null }),
    ],
    [
      "mais retidos do que clientes do anterior",
      retencaoDe({ atual: 2, anterior: null, retidos: 20, clientes_do_periodo_anterior: 10 }),
    ],
    ["retenção vazia fora dos 24 meses", { ...trintaDias(), retencao: vinteEQuatroMeses().retencao }],
    [
      "24 meses com algum anterior",
      { ...vinteEQuatroMeses(), satisfacao: { atual: 4.08, anterior: 4.0, avaliacoes: 20114 } },
    ],
    ["data fora do ISO", { ...trintaDias(), periodo: { inicio: "01/11/2026", fim: "2026-11-30" } }],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eIndicadoresDaDiretoria(corpo)).toBe(false);
  });
});
