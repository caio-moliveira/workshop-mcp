import { describe, expect, it } from "vitest";

import { ETAPAS } from "./etapas";
import { eFunilDoComercial, semLeads } from "./funil";

/** Uma resposta de `GET /comercial/funil?periodo=12m`, como a API a devolve. */
function resposta(): Record<string, unknown> {
  return {
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    etapas: [
      { etapa: "Novo", leads: 76 },
      { etapa: "Contatado", leads: 38 },
      { etapa: "Qualificado", leads: 40 },
      { etapa: "Proposta", leads: 27 },
      { etapa: "Fechado", leads: 110 },
      { etapa: "Perdido", leads: 455 },
    ],
  };
}

/** A resposta com o item da posição dada trocado. */
function comEtapa(posicao: number, troca: unknown): Record<string, unknown> {
  const etapas = [...(resposta().etapas as unknown[])];
  etapas[posicao] = troca;
  return { ...resposta(), etapas };
}

describe("validação da resposta do funil", () => {
  it("aceita a resposta do contrato", () => {
    expect(eFunilDoComercial(resposta())).toBe(true);
  });

  it("aceita zero numa etapa sem lead no período", () => {
    expect(eFunilDoComercial(comEtapa(1, { etapa: "Contatado", leads: 0 }))).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem período", { etapas: resposta().etapas }],
    ["período fora do ISO", { ...resposta(), periodo: { inicio: "01/12/2025", fim: "2026-11-30" } }],
    ["sem etapas", { periodo: resposta().periodo }],
    ["etapas como objeto", { ...resposta(), etapas: {} }],
    ["só cinco etapas", { ...resposta(), etapas: (resposta().etapas as unknown[]).slice(0, 5) }],
    [
      "etapas fora da ordem do funil",
      { ...resposta(), etapas: [...(resposta().etapas as unknown[])].reverse() },
    ],
    ["etapa fora do glossário", comEtapa(5, { etapa: "Descartado", leads: 455 })],
    ["etapa sem a grafia do glossário", comEtapa(0, { etapa: "novo", leads: 76 })],
    ["leads como texto", comEtapa(1, { etapa: "Contatado", leads: "38" })],
    ["leads fracionários", comEtapa(1, { etapa: "Contatado", leads: 1.5 })],
    ["leads negativos", comEtapa(1, { etapa: "Contatado", leads: -1 })],
    ["item sem leads", comEtapa(1, { etapa: "Contatado" })],
    ["item nulo", comEtapa(2, null)],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eFunilDoComercial(corpo)).toBe(false);
  });
});

describe("funil sem leads", () => {
  const periodo = { inicio: "2026-11-01", fim: "2026-11-30" };

  it("é vazio quando as seis etapas têm zero", () => {
    const etapas = ETAPAS.map((etapa) => ({ etapa, leads: 0 }));

    expect(semLeads({ periodo, etapas })).toBe(true);
  });

  it("não é vazio com um lead em qualquer etapa", () => {
    const etapas = ETAPAS.map((etapa) => ({ etapa, leads: etapa === "Perdido" ? 1 : 0 }));

    expect(semLeads({ periodo, etapas })).toBe(false);
  });
});
