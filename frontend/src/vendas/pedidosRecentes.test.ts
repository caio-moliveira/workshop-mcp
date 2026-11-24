import { describe, expect, it } from "vitest";

import { ePedidosRecentes } from "./pedidosRecentes";

/** Um pedido de `GET /vendas/pedidos-recentes`, como a API o devolve. */
function pedido(): Record<string, unknown> {
  return {
    numero: 29871,
    momento_compra: "2026-11-30T21:47:12.345678+00:00",
    cidade: "Belo Horizonte",
    uf: "MG",
    lojista: "Casa Aurora",
    rota: "SP → MG",
    valor: 249.9,
    pagamento: "Aprovado",
    entrega: "Em trânsito",
  };
}

function resposta(...pedidos: Record<string, unknown>[]): Record<string, unknown> {
  return { periodo: { inicio: "2025-12-01", fim: "2026-11-30" }, pedidos };
}

describe("validação da resposta de pedidos recentes", () => {
  it("aceita a resposta do contrato", () => {
    expect(ePedidosRecentes(resposta(pedido(), pedido()))).toBe(true);
  });

  it("aceita pedido sem entrega (pagamento recusado)", () => {
    expect(
      ePedidosRecentes(resposta({ ...pedido(), pagamento: "Recusado", entrega: null })),
    ).toBe(true);
  });

  it("aceita período sem pedidos", () => {
    expect(ePedidosRecentes(resposta())).toBe(true);
  });

  it("aceita o momento com o fuso de Brasília", () => {
    expect(
      ePedidosRecentes(resposta({ ...pedido(), momento_compra: "2026-11-30T18:47:12-03:00" })),
    ).toBe(true);
  });

  it("recusa mais de 20 pedidos", () => {
    expect(ePedidosRecentes(resposta(...Array.from({ length: 21 }, pedido)))).toBe(false);
  });

  it.each([
    ["nulo", null],
    ["sem a lista", { periodo: { inicio: "2025-12-01", fim: "2026-11-30" } }],
    ["lista que não é lista", { ...resposta(), pedidos: {} }],
    ["data do período fora do ISO", { ...resposta(), periodo: { inicio: "01/12/2025", fim: "2026-11-30" } }],
    ["número como texto", resposta({ ...pedido(), numero: "29871" })],
    ["valor como texto", resposta({ ...pedido(), valor: "249,90" })],
    ["momento sem fuso", resposta({ ...pedido(), momento_compra: "2026-11-30T21:47:12" })],
    ["momento que não é data", resposta({ ...pedido(), momento_compra: "ontem" })],
    ["situação de pagamento desconhecida", resposta({ ...pedido(), pagamento: "Pendente" })],
    ["situação de entrega desconhecida", resposta({ ...pedido(), entrega: "Extraviado" })],
    ["entrega ausente", resposta({ ...pedido(), entrega: undefined })],
    ["UF com três letras", resposta({ ...pedido(), uf: "MGG" })],
    ["sem lojista", resposta({ ...pedido(), lojista: undefined })],
  ])("recusa resposta fora do contrato: %s", (_, corpo) => {
    expect(ePedidosRecentes(corpo)).toBe(false);
  });
});
