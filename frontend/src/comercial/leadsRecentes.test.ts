import { describe, expect, it } from "vitest";

import { eLeadsRecentes } from "./leadsRecentes";

/** Um lead de `GET /comercial/leads` que ainda não fechou, como a API o devolve. */
function lead(): Record<string, unknown> {
  return {
    lead: 1500,
    empresa: "Comércio Aurora Ltda",
    canal: "Indicação",
    etapa: "Proposta",
    data_criacao: "2026-11-26",
    data_fechamento: null,
  };
}

function fechado(): Record<string, unknown> {
  return { ...lead(), etapa: "Fechado", data_fechamento: "2026-11-30" };
}

function resposta(...leads: unknown[]): Record<string, unknown> {
  return {
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    leads: leads.length ? leads : [lead(), fechado()],
  };
}

describe("validação da resposta de leads recentes do Comercial", () => {
  it("aceita a resposta do contrato", () => {
    expect(eLeadsRecentes(resposta())).toBe(true);
  });

  it("aceita a lista vazia", () => {
    expect(eLeadsRecentes({ ...resposta(), leads: [] })).toBe(true);
  });

  it.each(["Indicação", "Orgânico", "Mídia paga", "Eventos", "Prospecção ativa"])(
    "aceita o canal %s",
    (canal) => {
      expect(eLeadsRecentes(resposta({ ...lead(), canal }))).toBe(true);
    },
  );

  it.each(["Novo", "Contatado", "Qualificado", "Proposta", "Perdido"])(
    "aceita a etapa %s sem data de fechamento",
    (etapa) => {
      expect(eLeadsRecentes(resposta({ ...lead(), etapa }))).toBe(true);
    },
  );

  it("recusa mais de 20 leads", () => {
    const vinteEUm = Array.from({ length: 21 }, lead);

    expect(eLeadsRecentes(resposta(...vinteEUm))).toBe(false);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem leads", { ...resposta(), leads: undefined }],
    ["data do período fora do ISO", { ...resposta(), periodo: { inicio: "01/12/2025" } }],
    ["identificador como texto", resposta({ ...lead(), lead: "1500" })],
    ["identificador com casa decimal", resposta({ ...lead(), lead: 1.5 })],
    ["sem empresa", resposta({ ...lead(), empresa: undefined })],
    ["empresa vazia", resposta({ ...lead(), empresa: "" })],
    ["canal fora da enumeração", resposta({ ...lead(), canal: "Parcerias" })],
    ["canal sem acento", resposta({ ...lead(), canal: "Indicacao" })],
    ["etapa fora da enumeração", resposta({ ...lead(), etapa: "Negociação" })],
    ["data de criação fora do ISO", resposta({ ...lead(), data_criacao: "26/11/2026" })],
    ["data de fechamento fora do ISO", resposta({ ...fechado(), data_fechamento: "30/11/2026" })],
    ["data de fechamento ausente", resposta({ ...lead(), data_fechamento: undefined })],
    ["fechado sem data de fechamento", resposta({ ...fechado(), data_fechamento: null })],
    ["data de fechamento em quem não fechou", resposta({ ...fechado(), etapa: "Perdido" })],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eLeadsRecentes(corpo)).toBe(false);
  });
});
