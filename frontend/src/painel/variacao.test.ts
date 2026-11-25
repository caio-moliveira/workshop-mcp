import { describe, expect, it } from "vitest";

import { variacaoDoIndicador, variacaoEmPontos, variacaoRelativa } from "./variacao";

describe("variação em relação ao período anterior", () => {
  it("relativa, para contagens e receita", () => {
    expect(variacaoRelativa(1100, 1000)).toBeCloseTo(0.1);
    expect(variacaoRelativa(750, 1000)).toBeCloseTo(-0.25);
    expect(variacaoRelativa(1000, 1000)).toBe(0);
  });

  it("relativa não existe sem anterior ou com anterior zero", () => {
    expect(variacaoRelativa(1000, null)).toBeNull();
    expect(variacaoRelativa(1000, 0)).toBeNull();
  });

  it("em pontos percentuais, para taxas: a diferença entre as frações", () => {
    expect(variacaoEmPontos(0.112, 0.1)).toBeCloseTo(0.012);
    expect(variacaoEmPontos(0.08, 0.1)).toBeCloseTo(-0.02);
  });

  it("em pontos não existe se uma das taxas faltar", () => {
    expect(variacaoEmPontos(0.1, null)).toBeNull();
    expect(variacaoEmPontos(null, 0.1)).toBeNull();
  });
});

describe("a variação de um indicador, como aparece no cartão", () => {
  it("uma contagem que sobe, quando subir é bom", () => {
    expect(variacaoDoIndicador(1100, 1000, "relativa", "sobe")).toEqual({
      texto: "+10,0%",
      sentido: "sobe",
      tom: "bom",
    });
  });

  it("uma contagem que sobe, quando subir é ruim: reclamações", () => {
    expect(variacaoDoIndicador(148, 120, "relativa", "desce")).toEqual({
      texto: "+23,3%",
      sentido: "sobe",
      tom: "ruim",
    });
  });

  it("uma contagem que desce, quando subir é ruim: produtos mal avaliados", () => {
    expect(variacaoDoIndicador(4, 26, "relativa", "desce")).toEqual({
      texto: "-84,6%",
      sentido: "desce",
      tom: "bom",
    });
  });

  it("uma taxa em pontos percentuais, quando descer é bom", () => {
    expect(variacaoDoIndicador(0.112, 0.1, "pontos_percentuais", "desce")).toEqual({
      texto: "+1,2 p.p.",
      sentido: "sobe",
      tom: "ruim",
    });
  });

  it("a nota média em pontos, com duas casas", () => {
    expect(variacaoDoIndicador(4.12, 4.05, "pontos", "sobe")).toEqual({
      texto: "+0,07",
      sentido: "sobe",
      tom: "bom",
    });
    expect(variacaoDoIndicador(3.9, 4.25, "pontos", "sobe")).toEqual({
      texto: "-0,35",
      sentido: "desce",
      tom: "ruim",
    });
  });

  it("não existe sem período anterior com que comparar", () => {
    expect(variacaoDoIndicador(1000, null, "relativa", "sobe")).toBeNull();
    expect(variacaoDoIndicador(1000, 0, "relativa", "sobe")).toBeNull();
    expect(variacaoDoIndicador(null, 0.1, "pontos_percentuais", "sobe")).toBeNull();
    expect(variacaoDoIndicador(4.1, null, "pontos", "sobe")).toBeNull();
  });

  it("uma variação que aparece como zero é neutra e sem seta", () => {
    // -0,0349 p.p.: a taxa de aprovação em 12 meses na carga padrão aparece como "0,0 p.p.".
    expect(variacaoDoIndicador(0.899651, 0.9, "pontos_percentuais", "sobe")).toEqual({
      texto: "0,0 p.p.",
      sentido: "estavel",
      tom: "neutro",
    });
    expect(variacaoDoIndicador(1000.4, 1000, "relativa", "desce")).toMatchObject({
      sentido: "estavel",
      tom: "neutro",
    });
    expect(variacaoDoIndicador(4.104, 4.1, "pontos", "desce")).toEqual({
      texto: "0,00",
      sentido: "estavel",
      tom: "neutro",
    });
  });

  it("a partir de meia casa a variação aparece, com seta e tom", () => {
    expect(variacaoDoIndicador(0.1006, 0.1, "pontos_percentuais", "desce")).toMatchObject({
      sentido: "sobe",
      tom: "ruim",
    });
    expect(variacaoDoIndicador(4.094, 4.1, "pontos", "sobe")).toMatchObject({
      texto: "-0,01",
      sentido: "desce",
      tom: "ruim",
    });
  });
});
