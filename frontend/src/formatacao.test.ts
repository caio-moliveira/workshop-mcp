import { describe, expect, it } from "vitest";

import {
  formatarData,
  formatarDataHora,
  formatarHora,
  formatarDiferencaDeNota,
  formatarMoeda,
  formatarMoedaCompacta,
  formatarNumero,
  formatarNota,
  formatarNumeroCompacto,
  formatarPercentual,
  formatarPontosPercentuais,
  formatarVariacaoRelativa,
} from "./formatacao";

// O Intl separa o símbolo da moeda com um espaço não separável.
const ESPACO = " ";

describe("formatação em pt-BR", () => {
  it("moeda em reais, com centavos", () => {
    expect(formatarMoeda(1234567.8)).toBe(`R$${ESPACO}1.234.567,80`);
    expect(formatarMoeda(0)).toBe(`R$${ESPACO}0,00`);
  });

  it("nota média de 1 a 5, com duas casas", () => {
    expect(formatarNota(4.1234)).toBe("4,12");
    expect(formatarNota(3)).toBe("3,00");
  });

  it("contagens com separador de milhar", () => {
    expect(formatarNumero(29999)).toBe("29.999");
  });

  it("percentual de uma fração, com uma casa", () => {
    expect(formatarPercentual(0.1234)).toBe("12,3%");
    expect(formatarPercentual(0.9)).toBe("90,0%");
    expect(formatarPercentual(1)).toBe("100,0%");
  });

  it("variação relativa com sinal", () => {
    expect(formatarVariacaoRelativa(0.0849)).toBe("+8,5%");
    expect(formatarVariacaoRelativa(-0.2)).toBe("-20,0%");
    expect(formatarVariacaoRelativa(0)).toBe("0,0%");
  });

  it("pontos percentuais de uma diferença entre frações, com sinal", () => {
    expect(formatarPontosPercentuais(0.012)).toBe("+1,2 p.p.");
    expect(formatarPontosPercentuais(-0.0349)).toBe("-3,5 p.p.");
    expect(formatarPontosPercentuais(0)).toBe("0,0 p.p.");
  });

  it("diferença entre notas médias, em pontos da nota, com duas casas e sinal", () => {
    expect(formatarDiferencaDeNota(0.07)).toBe("+0,07");
    expect(formatarDiferencaDeNota(-0.354)).toBe("-0,35");
    expect(formatarDiferencaDeNota(0)).toBe("0,00");
  });

  it("instante ISO como data e hora de Brasília, venha com o fuso que vier", () => {
    expect(formatarDataHora("2026-11-30T14:05:09-03:00")).toBe("30/11/2026, 14:05");
    expect(formatarDataHora("2026-11-30T17:05:09+00:00")).toBe("30/11/2026, 14:05");
  });

  it("instante ISO só como hora de Brasília, com os segundos", () => {
    expect(formatarHora("2026-11-30T17:05:09+00:00")).toBe("14:05:09");
    expect(formatarHora("2026-11-01T02:30:00+00:00")).toBe("23:30:00");
  });

  it("instante da madrugada em UTC cai na noite anterior em Brasília", () => {
    expect(formatarDataHora("2026-11-01T02:30:00+00:00")).toBe("31/10/2026, 23:30");
  });

  it("data ISO no formato brasileiro, sem deslocar o dia pelo fuso", () => {
    expect(formatarData("2026-11-30")).toBe("30/11/2026");
    expect(formatarData("2024-12-01")).toBe("01/12/2024");
  });

  it("moeda e contagem compactas, para os eixos dos gráficos", () => {
    expect(formatarMoedaCompacta(0)).toBe(`R$${ESPACO}0`);
    expect(formatarMoedaCompacta(12500)).toBe(`R$${ESPACO}12,5${ESPACO}mil`);
    expect(formatarMoedaCompacta(4321987.65)).toBe(`R$${ESPACO}4,3${ESPACO}mi`);
    expect(formatarNumeroCompacto(950)).toBe("950");
    expect(formatarNumeroCompacto(1500)).toBe(`1,5${ESPACO}mil`);
  });
});
