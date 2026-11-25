import { describe, expect, it } from "vitest";

import { eIndicadoresDeProdutos } from "./indicadores";

/** Uma resposta de `GET /produtos/indicadores?periodo=12m`, como a API a devolve. */
function resposta(): Record<string, unknown> {
  return {
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    catalogo: 2000,
    produtos_avaliados: { atual: 1826, anterior: 1700 },
    nota_media: { atual: 4.12, anterior: 4.05 },
    avaliacoes: { atual: 11594, anterior: 8520 },
    reclamacoes: { atual: 1472, anterior: 1079 },
    produtos_mal_avaliados: { atual: 20, anterior: 18 },
  };
}

describe("validação da resposta de indicadores de Produtos", () => {
  it("aceita a resposta do contrato", () => {
    expect(eIndicadoresDeProdutos(resposta())).toBe(true);
  });

  it("aceita o anterior nulo (24 meses) e a nota média nula sem avaliações", () => {
    const corpo = resposta();
    corpo.produtos_avaliados = { atual: 0, anterior: null };
    corpo.nota_media = { atual: null, anterior: null };
    corpo.avaliacoes = { atual: 0, anterior: null };
    corpo.reclamacoes = { atual: 0, anterior: null };
    corpo.produtos_mal_avaliados = { atual: 0, anterior: null };

    expect(eIndicadoresDeProdutos(corpo)).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem catálogo", { ...resposta(), catalogo: undefined }],
    ["catálogo com variação", { ...resposta(), catalogo: { atual: 2000, anterior: 2000 } }],
    ["sem reclamações", { ...resposta(), reclamacoes: undefined }],
    ["contagem nula", { ...resposta(), avaliacoes: { atual: null, anterior: null } }],
    ["número como texto", { ...resposta(), produtos_mal_avaliados: { atual: "4", anterior: 1 } }],
    ["anterior ausente", { ...resposta(), nota_media: { atual: 4.1 } }],
    ["data fora do ISO", { ...resposta(), periodo: { inicio: "01/12/2025", fim: "2026-11-30" } }],
    ["NaN", { ...resposta(), produtos_avaliados: { atual: Number.NaN, anterior: null } }],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eIndicadoresDeProdutos(corpo)).toBe(false);
  });
});
