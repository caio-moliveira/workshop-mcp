import { describe, expect, it } from "vitest";

import { eIndicadoresDoComercial } from "./indicadores";

/** Uma resposta de `GET /comercial/indicadores?periodo=12m`, como a API a devolve. */
function resposta(): Record<string, unknown> {
  return {
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    leads: { atual: 746, anterior: 580 },
    leads_em_negociacao: 181,
    novos_lojistas: { atual: 126, anterior: 94 },
    dias_ate_fechar: 44.198,
    conversao: { atual: 0.1689, anterior: 0.1621 },
    principal_canal: "Mídia paga",
    parcela_do_principal_canal: 0.2976,
  };
}

describe("validação da resposta de indicadores do Comercial", () => {
  it("aceita a resposta do contrato", () => {
    expect(eIndicadoresDoComercial(resposta())).toBe(true);
  });

  it("aceita o anterior nulo (24 meses)", () => {
    const corpo = resposta();
    corpo.leads = { atual: 1326, anterior: null };
    corpo.novos_lojistas = { atual: 220, anterior: null };
    corpo.conversao = { atual: 0.1659, anterior: null };

    expect(eIndicadoresDoComercial(corpo)).toBe(true);
  });

  it("aceita o período sem lead: conversão, principal canal e parcela vazios", () => {
    const corpo = resposta();
    corpo.leads = { atual: 0, anterior: 12 };
    corpo.leads_em_negociacao = 0;
    corpo.conversao = { atual: null, anterior: 0.25 };
    corpo.principal_canal = null;
    corpo.parcela_do_principal_canal = null;

    expect(eIndicadoresDoComercial(corpo)).toBe(true);
  });

  it("aceita o período sem novo lojista: dias até fechar vazios", () => {
    const corpo = resposta();
    corpo.novos_lojistas = { atual: 0, anterior: 3 };
    corpo.dias_ate_fechar = null;
    corpo.conversao = { atual: 0, anterior: 0.1 };

    expect(eIndicadoresDoComercial(corpo)).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem leads", { ...resposta(), leads: undefined }],
    ["contagem nula", { ...resposta(), novos_lojistas: { atual: null, anterior: null } }],
    ["em negociação com variação", { ...resposta(), leads_em_negociacao: { atual: 1, anterior: 1 } }],
    ["número como texto", { ...resposta(), leads: { atual: "746", anterior: 580 } }],
    ["anterior ausente", { ...resposta(), conversao: { atual: 0.16 } }],
    ["dias ausentes", { ...resposta(), dias_ate_fechar: undefined }],
    ["canal fora da enumeração", { ...resposta(), principal_canal: "Televisão" }],
    ["canal como número", { ...resposta(), principal_canal: 3 }],
    ["canal sem parcela", { ...resposta(), parcela_do_principal_canal: null }],
    ["parcela sem canal", { ...resposta(), principal_canal: null }],
    ["data fora do ISO", { ...resposta(), periodo: { inicio: "01/12/2025", fim: "2026-11-30" } }],
    ["NaN", { ...resposta(), leads: { atual: Number.NaN, anterior: null } }],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eIndicadoresDoComercial(corpo)).toBe(false);
  });
});
