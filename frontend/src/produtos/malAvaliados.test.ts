import { describe, expect, it } from "vitest";

import { eMalAvaliados } from "./malAvaliados";

/** Um produto de `GET /produtos/mal-avaliados`, como a API o devolve. */
function produto(): Record<string, unknown> {
  return {
    produto: 1417,
    nome_do_produto: "Fone de ouvido Bluetooth Max",
    categoria: "Eletrônicos",
    preco: 189.9,
    nota_media: 1.6666666666666667,
    avaliacoes: 3,
  };
}

function resposta(...produtos: unknown[]): Record<string, unknown> {
  return { periodo: { inicio: "2026-11-01", fim: "2026-11-30" }, produtos };
}

describe("validação da resposta de produtos mal avaliados", () => {
  it("aceita a resposta do contrato", () => {
    expect(eMalAvaliados(resposta(produto(), { ...produto(), produto: 2 }))).toBe(true);
  });

  it("aceita período sem produto mal avaliado", () => {
    expect(eMalAvaliados(resposta())).toBe(true);
  });

  it("aceita até 50 produtos e recusa mais que isso", () => {
    expect(eMalAvaliados(resposta(...Array.from({ length: 50 }, produto)))).toBe(true);
    expect(eMalAvaliados(resposta(...Array.from({ length: 51 }, produto)))).toBe(false);
  });

  it.each([
    ["nulo", null],
    ["lista no lugar do objeto", []],
    ["sem período", { produtos: [] }],
    ["sem produtos", { periodo: { inicio: "2026-11-01", fim: "2026-11-30" } }],
    ["produtos não é lista", { ...resposta(), produtos: {} }],
    ["data fora do ISO", { ...resposta(), periodo: { inicio: "01/11/2026", fim: "2026-11-30" } }],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eMalAvaliados(corpo)).toBe(false);
  });

  it.each([
    ["identificador decimal", { produto: 1.5 }],
    ["identificador como texto", { produto: "1417" }],
    ["sem nome", { nome_do_produto: "" }],
    ["sem categoria", { categoria: undefined }],
    ["preço como texto", { preco: "189,90" }],
    ["nota média nula", { nota_media: null }],
    ["nota média NaN", { nota_media: Number.NaN }],
    ["avaliações decimais", { avaliacoes: 3.5 }],
  ])("recusa produto fora do contrato: %s", (_, troca) => {
    expect(eMalAvaliados(resposta({ ...produto(), ...troca }))).toBe(false);
  });
});
