import { describe, expect, it } from "vitest";

import {
  canaisPorNovosLojistas,
  eDesempenhoDosCanais,
  type DesempenhoDoCanal,
} from "./desempenhoDosCanais";

function canal(
  nome: string,
  leads: number,
  novosLojistas: number,
  dias: number | null = novosLojistas === 0 ? null : 44.5,
): DesempenhoDoCanal {
  return {
    canal: nome as DesempenhoDoCanal["canal"],
    leads,
    novos_lojistas: novosLojistas,
    conversao: leads === 0 ? null : novosLojistas / leads,
    dias_ate_fechar: dias,
  };
}

/** Uma resposta de `GET /comercial/canais`, como a API a devolve, com os dois vazios. */
function resposta(): Record<string, unknown> {
  return {
    periodo: { inicio: "2026-11-01", fim: "2026-11-30" },
    canais: [
      canal("Indicação", 10, 3),
      canal("Mídia paga", 16, 4),
      canal("Orgânico", 19, 2),
      // Com lead e sem fechamento: conversão zero e dias vazios.
      canal("Prospecção ativa", 12, 0),
      // Sem lead criado no período, mas com fechamento de lead antigo: conversão vazia.
      canal("Eventos", 0, 1),
    ],
  };
}

function comCanal(troca: unknown): Record<string, unknown> {
  return { ...resposta(), canais: [troca, ...(resposta().canais as unknown[]).slice(1)] };
}

describe("validação da resposta do desempenho dos canais", () => {
  it("aceita a resposta do contrato, com conversão vazia e dias vazios", () => {
    expect(eDesempenhoDosCanais(resposta())).toBe(true);
  });

  it("aceita conversão acima de 1: leads antigos podem fechar num período de poucos leads", () => {
    expect(eDesempenhoDosCanais(comCanal(canal("Indicação", 2, 3)))).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem período", { canais: resposta().canais }],
    ["sem canais", { periodo: resposta().periodo }],
    ["canais como objeto", { ...resposta(), canais: {} }],
    ["só quatro canais", { ...resposta(), canais: (resposta().canais as unknown[]).slice(1) }],
    ["canal repetido", comCanal(canal("Mídia paga", 10, 3))],
    ["item nulo", comCanal(null)],
    ["canal fora da enumeração", comCanal(canal("Origem", 10, 3))],
    ["canal sem acento", comCanal(canal("Indicacao", 10, 3))],
    ["leads como texto", comCanal({ ...canal("Indicação", 10, 3), leads: "10" })],
    ["leads fracionários", comCanal({ ...canal("Indicação", 10, 3), leads: 1.5 })],
    ["novos lojistas negativos", comCanal({ ...canal("Indicação", 10, 3), novos_lojistas: -1 })],
    ["sem conversão", comCanal({ ...canal("Indicação", 10, 3), conversao: undefined })],
    ["conversão negativa", comCanal({ ...canal("Indicação", 10, 3), conversao: -0.1 })],
    ["conversão vazia com leads", comCanal({ ...canal("Indicação", 10, 3), conversao: null })],
    ["conversão sem leads", comCanal({ ...canal("Indicação", 0, 1), conversao: 0.5 })],
    ["sem dias", comCanal({ ...canal("Indicação", 10, 3), dias_ate_fechar: undefined })],
    ["dias negativos", comCanal(canal("Indicação", 10, 3, -1))],
    ["dias vazios com fechamento", comCanal(canal("Indicação", 10, 3, null))],
    ["dias sem fechamento", comCanal(canal("Indicação", 10, 0, 30))],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(eDesempenhoDosCanais(corpo)).toBe(false);
  });
});

describe("os canais do gráfico de novos lojistas", () => {
  it("vêm do canal com mais novos lojistas para o de menos, com o empate pelo nome", () => {
    const canais = [
      canal("Indicação", 10, 3),
      canal("Mídia paga", 16, 4),
      canal("Orgânico", 19, 3),
      canal("Prospecção ativa", 12, 0),
      canal("Eventos", 0, 1),
    ];

    expect(canaisPorNovosLojistas(canais).map((item) => item.canal)).toEqual([
      "Mídia paga",
      "Indicação",
      "Orgânico",
      "Eventos",
      "Prospecção ativa",
    ]);
  });

  it("não muda a ordem da resposta, que é a da tabela", () => {
    const canais = [canal("Indicação", 10, 3), canal("Mídia paga", 16, 4)];

    canaisPorNovosLojistas(canais);

    expect(canais.map((item) => item.canal)).toEqual(["Indicação", "Mídia paga"]);
  });
});
