import { describe, expect, it } from "vitest";

import { eTendenciaDaDiretoria, semClientes } from "./tendencia";

/** Um ponto de `GET /diretoria/tendencia`, como a API o devolve, com os campos dados trocados. */
function ponto(troca: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    inicio: "2026-11-23",
    receita: 70663.29,
    taxa_de_recompra: 13 / 67,
    clientes: 67,
    clientes_com_recompra: 13,
    satisfacao: 3.6444,
    avaliacoes: 45,
    taxa_de_atraso: 0,
    entregues: 52,
    atrasos: 0,
    ...troca,
  };
}

/** Uma resposta de 30 dias, com um último dia ainda sem entrega. */
function resposta(pontos: unknown[] = [ponto(), ponto({ inicio: "2026-11-30", taxa_de_atraso: null, entregues: 0 })]) {
  return {
    periodo: { inicio: "2026-11-01", fim: "2026-11-30" },
    agrupamento: "dia",
    pontos,
  };
}

describe("validação da resposta da tendência da Diretoria", () => {
  it("aceita a resposta do contrato, com um ponto sem entrega", () => {
    expect(eTendenciaDaDiretoria(resposta())).toBe(true);
  });

  it.each(["dia", "semana", "mes"])("aceita o agrupamento %s", (agrupamento) => {
    expect(eTendenciaDaDiretoria({ ...resposta(), agrupamento })).toBe(true);
  });

  it("aceita o ponto sem cliente, sem avaliação e sem entrega, com os indicadores vazios", () => {
    const vazio = ponto({
      receita: 0,
      taxa_de_recompra: null,
      clientes: 0,
      clientes_com_recompra: 0,
      satisfacao: null,
      avaliacoes: 0,
      taxa_de_atraso: null,
      entregues: 0,
      atrasos: 0,
    });

    expect(eTendenciaDaDiretoria(resposta([vazio]))).toBe(true);
  });

  it("aceita a lista vazia de pontos", () => {
    expect(eTendenciaDaDiretoria(resposta([]))).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["agrupamento desconhecido", { ...resposta(), agrupamento: "ano" }],
    ["sem período", { agrupamento: "dia", pontos: [] }],
    ["pontos como objeto", { ...resposta(), pontos: {} }],
    ["data fora do ISO", resposta([ponto({ inicio: "23/11/2026" })])],
    ["receita como texto", resposta([ponto({ receita: "1" })])],
    ["receita negativa", resposta([ponto({ receita: -1 })])],
    ["clientes fracionário", resposta([ponto({ clientes: 1.5 })])],
    ["recompra acima dos clientes", resposta([ponto({ clientes_com_recompra: 68 })])],
    ["taxa de recompra vazia com clientes", resposta([ponto({ taxa_de_recompra: null })])],
    [
      "taxa de recompra sem clientes",
      resposta([ponto({ clientes: 0, clientes_com_recompra: 0, taxa_de_recompra: 0 })]),
    ],
    ["taxa de recompra acima de 1", resposta([ponto({ taxa_de_recompra: 1.2 })])],
    ["satisfação acima de 5", resposta([ponto({ satisfacao: 5.5 })])],
    ["satisfação abaixo de 1", resposta([ponto({ satisfacao: 0.5 })])],
    ["satisfação vazia com avaliações", resposta([ponto({ satisfacao: null })])],
    ["satisfação sem avaliação", resposta([ponto({ avaliacoes: 0 })])],
    ["atrasos acima dos entregues", resposta([ponto({ atrasos: 53 })])],
    ["taxa de atraso vazia com entregues", resposta([ponto({ taxa_de_atraso: null })])],
    ["taxa de atraso sem entregue", resposta([ponto({ entregues: 0, taxa_de_atraso: 0 })])],
    ["sem taxa de atraso", resposta([{ ...ponto(), taxa_de_atraso: undefined }])],
  ])("recusa %s", (_nome, valor) => {
    expect(eTendenciaDaDiretoria(valor)).toBe(false);
  });
});

describe("tendência sem clientes", () => {
  it("é vazia quando nenhum ponto tem cliente", () => {
    const vazio = ponto({ clientes: 0, clientes_com_recompra: 0, taxa_de_recompra: null });
    const dados = resposta([vazio, vazio]);

    expect(eTendenciaDaDiretoria(dados) && semClientes(dados)).toBe(true);
  });

  it("não é vazia quando um ponto tem cliente", () => {
    const dados = resposta();

    expect(eTendenciaDaDiretoria(dados) && semClientes(dados)).toBe(false);
  });

  it("é vazia sem pontos", () => {
    const dados = resposta([]);

    expect(eTendenciaDaDiretoria(dados) && semClientes(dados)).toBe(true);
  });
});
