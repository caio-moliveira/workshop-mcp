import { describe, expect, it } from "vitest";

import {
  sentidoDaVariacao,
  tomDaVariacao,
  variacaoEmPontos,
  variacaoRelativa,
} from "./variacao";

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

  it("o tom depende de qual direção é boa", () => {
    expect(tomDaVariacao(0.1, "sobe")).toBe("bom");
    expect(tomDaVariacao(-0.1, "sobe")).toBe("ruim");
    expect(tomDaVariacao(0.01, "desce")).toBe("ruim");
    expect(tomDaVariacao(-0.01, "desce")).toBe("bom");
    expect(tomDaVariacao(0, "sobe")).toBe("neutro");
  });

  it("uma variação que aparece como zero, com uma casa, é neutra", () => {
    // -0,0349 p.p.: a taxa de aprovação em 12 meses na carga padrão aparece como "0,0 p.p.".
    expect(tomDaVariacao(-0.000349, "sobe")).toBe("neutro");
    expect(tomDaVariacao(0.0004, "desce")).toBe("neutro");
    expect(tomDaVariacao(0.0005, "sobe")).toBe("bom");
    expect(tomDaVariacao(-0.0006, "desce")).toBe("bom");
  });

  it("o sentido da seta segue o valor que aparece", () => {
    expect(sentidoDaVariacao(0.272)).toBe("sobe");
    expect(sentidoDaVariacao(-0.0118)).toBe("desce");
    expect(sentidoDaVariacao(-0.000349)).toBe("estavel");
    expect(sentidoDaVariacao(0)).toBe("estavel");
  });
});
