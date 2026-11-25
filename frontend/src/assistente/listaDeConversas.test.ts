import { describe, expect, it } from "vitest";

import {
  LISTA_CARREGANDO,
  listaComErro,
  listaRecebida,
  semAConversa,
  vazia,
  type ListaDeConversas,
} from "./listaDeConversas";

// Como a rota `GET /conversas` devolve: da última atividade mais recente para a mais antiga.
const DA_API = {
  conversas: [
    {
      id: "conversa-2",
      titulo: "Como foi o faturamento?",
      ultima_atividade: "2026-11-25T14:02:00+00:00",
    },
    {
      id: "conversa-1",
      titulo: "Quais lojistas atrasam mais?",
      ultima_atividade: "2026-11-24T09:30:00+00:00",
    },
  ],
};

describe("lista de conversas", () => {
  it("começa carregando, sem conversas e sem estar vazia", () => {
    expect(LISTA_CARREGANDO).toEqual({ situacao: "carregando" });
    expect(vazia(LISTA_CARREGANDO)).toBe(false);
  });

  it("carregada, mantém a ordem da API, com título e última atividade", () => {
    const lista = listaRecebida(DA_API);

    expect(lista).toEqual({
      situacao: "carregada",
      conversas: [
        {
          id: "conversa-2",
          titulo: "Como foi o faturamento?",
          ultimaAtividade: "2026-11-25T14:02:00+00:00",
        },
        {
          id: "conversa-1",
          titulo: "Quais lojistas atrasam mais?",
          ultimaAtividade: "2026-11-24T09:30:00+00:00",
        },
      ],
    });
    expect(vazia(lista)).toBe(false);
  });

  it("sem conversas, está vazia", () => {
    const lista = listaRecebida({ conversas: [] });

    expect(lista).toEqual({ situacao: "carregada", conversas: [] });
    expect(vazia(lista)).toBe(true);
  });

  it("com a API fora do ar, fica com erro, e não vazia", () => {
    expect(listaComErro()).toEqual({ situacao: "erro" });
    expect(vazia(listaComErro())).toBe(false);
  });

  it.each([
    ["nada", null],
    ["sem a lista", {}],
    ["lista que não é lista", { conversas: "muitas" }],
    ["conversa sem título", { conversas: [{ id: "c", ultima_atividade: "2026-11-25" }] }],
    ["identificador que não é texto", { conversas: [{ id: 1, titulo: "t", ultima_atividade: "x" }] }],
  ])("uma resposta fora do contrato vira erro: %s", (_, valor) => {
    expect(listaRecebida(valor)).toEqual({ situacao: "erro" });
  });

  it("apagar tira só a conversa apagada", () => {
    const lista = semAConversa(listaRecebida(DA_API), "conversa-2");

    expect(lista).toMatchObject({
      situacao: "carregada",
      conversas: [{ id: "conversa-1" }],
    });
  });

  it("apagar a última deixa a lista vazia", () => {
    const sobra = semAConversa(listaRecebida(DA_API), "conversa-2");

    expect(vazia(semAConversa(sobra, "conversa-1"))).toBe(true);
  });

  it.each<[string, ListaDeConversas]>([
    ["carregando", LISTA_CARREGANDO],
    ["com erro", listaComErro()],
  ])("apagar com a lista %s não muda nada", (_, lista) => {
    expect(semAConversa(lista, "conversa-1")).toBe(lista);
  });
});
