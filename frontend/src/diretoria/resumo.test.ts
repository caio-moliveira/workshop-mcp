import { describe, expect, it } from "vitest";

import { eResumoPorCanal, semPedidos, type ResumoDoCanal } from "./resumo";

function canal(
  nome: string,
  pedidos: number,
  entregues: number,
  atrasos: number,
  avaliacoes = Math.round(entregues * 0.7),
  clientes = pedidos,
): ResumoDoCanal {
  return {
    canal: nome as ResumoDoCanal["canal"],
    pedidos,
    receita: pedidos * 950.5,
    taxa_de_atraso: entregues === 0 ? null : atrasos / entregues,
    entregues,
    atrasos,
    satisfacao: avaliacoes === 0 ? null : 4.1,
    avaliacoes,
    taxa_de_recompra: clientes === 0 ? null : 0.1,
    clientes,
    clientes_com_recompra: Math.round(clientes * 0.1),
  };
}

/** Uma resposta de `GET /diretoria/resumo`, como a API a devolve, com um canal sem entrega. */
function resposta(): Record<string, unknown> {
  return {
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    canais: [
      canal("Mídia paga", 9214, 8569, 1094),
      canal("Prospecção ativa", 1510, 1384, 89),
      canal("Orgânico", 3448, 3212, 161),
      canal("Indicação", 1686, 1576, 41),
      // Pedidos só em trânsito, sem avaliação: as duas taxas vazias.
      canal("Eventos", 12, 0, 0, 0),
    ],
  };
}

function comCanal(troca: unknown): Record<string, unknown> {
  return { ...resposta(), canais: [troca, ...(resposta().canais as unknown[]).slice(1)] };
}

describe("validação da resposta do resumo por canal", () => {
  it("aceita a resposta do contrato, com taxas vazias", () => {
    expect(eResumoPorCanal(resposta())).toBe(true);
  });

  it.each([
    ["nulo", null],
    ["lista", []],
    ["sem período", { canais: resposta().canais }],
    ["sem canais", { periodo: resposta().periodo }],
    ["só quatro canais", { ...resposta(), canais: (resposta().canais as unknown[]).slice(1) }],
    ["canal repetido", comCanal(canal("Eventos", 10, 5, 1))],
    ["canal fora da enumeração", comCanal(canal("Afiliados", 10, 5, 1))],
    ["pedidos negativos", comCanal({ ...canal("Mídia paga", 10, 5, 1), pedidos: -1 })],
    ["pedidos fracionários", comCanal({ ...canal("Mídia paga", 10, 5, 1), pedidos: 1.5 })],
    ["receita negativa", comCanal({ ...canal("Mídia paga", 10, 5, 1), receita: -1 })],
    ["mais atrasos que entregues", comCanal({ ...canal("Mídia paga", 10, 5, 1), atrasos: 6 })],
    [
      "taxa de atraso vazia com entregues",
      comCanal({ ...canal("Mídia paga", 10, 5, 1), taxa_de_atraso: null }),
    ],
    [
      "taxa de atraso sem entregues",
      comCanal({ ...canal("Mídia paga", 10, 0, 0), taxa_de_atraso: 0 }),
    ],
    ["taxa de atraso acima de 1", comCanal({ ...canal("Mídia paga", 10, 5, 1), taxa_de_atraso: 2 })],
    [
      "satisfação vazia com avaliações",
      comCanal({ ...canal("Mídia paga", 10, 5, 1), satisfacao: null }),
    ],
    ["satisfação abaixo de 1", comCanal({ ...canal("Mídia paga", 10, 5, 1), satisfacao: 0.5 })],
    [
      "taxa de recompra vazia com clientes",
      comCanal({ ...canal("Mídia paga", 10, 5, 1), taxa_de_recompra: null }),
    ],
    [
      "mais clientes com recompra que clientes",
      comCanal({ ...canal("Mídia paga", 10, 5, 1), clientes_com_recompra: 11 }),
    ],
    [
      "contagem como texto",
      comCanal({ ...canal("Mídia paga", 10, 5, 1), avaliacoes: "3" }),
    ],
  ])("recusa %s", (_, valor) => {
    expect(eResumoPorCanal(valor)).toBe(false);
  });
});

describe("período sem pedidos", () => {
  const canais = resposta().canais as ResumoDoCanal[];

  it("não é vazio quando algum canal tem pedido", () => {
    expect(semPedidos(canais)).toBe(false);
  });

  it("é vazio quando nenhum canal tem pedido", () => {
    expect(semPedidos(canais.map((item) => canal(item.canal, 0, 0, 0, 0, 0)))).toBe(true);
  });
});
