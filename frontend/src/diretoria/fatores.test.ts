import { describe, expect, it } from "vitest";

import { eFatoresDeRecompra, semGrupos } from "./fatores";

/** Uma resposta de `GET /diretoria/fatores-de-recompra?periodo=12m`, como a API a devolve. */
function dozeMeses(): Record<string, unknown> {
  return {
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    primeira_entrega: [
      {
        grupo: "No prazo",
        clientes: 13660,
        clientes_com_recompra: 1204,
        taxa_de_recompra: 1204 / 13660,
      },
      {
        grupo: "Com atraso",
        clientes: 1313,
        clientes_com_recompra: 0,
        taxa_de_recompra: 0,
      },
    ],
    primeira_nota: [
      {
        grupo: "1 ou 2",
        clientes: 1258,
        clientes_com_recompra: 10,
        taxa_de_recompra: 10 / 1258,
      },
      {
        grupo: "3",
        clientes: 1044,
        clientes_com_recompra: 107,
        taxa_de_recompra: 107 / 1044,
      },
      {
        grupo: "4 ou 5",
        clientes: 8408,
        clientes_com_recompra: 1087,
        taxa_de_recompra: 1087 / 8408,
      },
    ],
    faixa_de_atraso: [
      { grupo: "No prazo", avaliacoes: 10514, satisfacao: 4.2762 },
      { grupo: "Até 7 dias", avaliacoes: 533, satisfacao: 2.8311 },
      { grupo: "Mais de 7 dias", avaliacoes: 547, satisfacao: 1.7477 },
    ],
  };
}

type Bloco = "primeira_entrega" | "primeira_nota" | "faixa_de_atraso";

/** A resposta de 12 meses com um grupo trocado por outro, para os casos inválidos. */
function comGrupo(bloco: Bloco, indice: number, grupo: Record<string, unknown>) {
  const corpo = dozeMeses();
  const grupos = [...(corpo[bloco] as Record<string, unknown>[])];
  grupos[indice] = { ...grupos[indice], ...grupo };
  return { ...corpo, [bloco]: grupos };
}

/** Todos os grupos vazios: um período sem cliente e sem avaliação. */
function vazio(): Record<string, unknown> {
  const corpo = dozeMeses();
  const recompraVazia = (item: Record<string, unknown>) => ({
    ...item,
    clientes: 0,
    clientes_com_recompra: 0,
    taxa_de_recompra: null,
  });
  return {
    ...corpo,
    primeira_entrega: (corpo.primeira_entrega as Record<string, unknown>[]).map(recompraVazia),
    primeira_nota: (corpo.primeira_nota as Record<string, unknown>[]).map(recompraVazia),
    faixa_de_atraso: (corpo.faixa_de_atraso as Record<string, unknown>[]).map((item) => ({
      ...item,
      avaliacoes: 0,
      satisfacao: null,
    })),
  };
}

describe("validação da resposta dos fatores de recompra", () => {
  it("aceita a resposta do contrato, com os três blocos", () => {
    expect(eFatoresDeRecompra(dozeMeses())).toBe(true);
  });

  it("aceita os grupos vazios, com a taxa e a satisfação nulas", () => {
    expect(eFatoresDeRecompra(vazio())).toBe(true);
  });

  it("recusa um bloco faltando ou um grupo fora da enumeração", () => {
    const semNota = dozeMeses();
    delete semNota.primeira_nota;
    expect(eFatoresDeRecompra(semNota)).toBe(false);
    expect(eFatoresDeRecompra(comGrupo("primeira_nota", 0, { grupo: "Sem avaliação" }))).toBe(
      false,
    );
    expect(eFatoresDeRecompra(comGrupo("primeira_entrega", 1, { grupo: "Em trânsito" }))).toBe(
      false,
    );
  });

  it("recusa os grupos fora da ordem ou repetidos", () => {
    const corpo = dozeMeses();
    const entrega = corpo.primeira_entrega as unknown[];
    expect(
      eFatoresDeRecompra({
        ...corpo,
        primeira_entrega: [...entrega].reverse(),
      }),
    ).toBe(false);
    expect(
      eFatoresDeRecompra({
        ...corpo,
        primeira_entrega: [entrega[0], entrega[0]],
      }),
    ).toBe(false);
  });

  it("recusa mais clientes com recompra do que clientes no grupo", () => {
    expect(
      eFatoresDeRecompra(
        comGrupo("primeira_nota", 2, {
          clientes: 10,
          clientes_com_recompra: 11,
        }),
      ),
    ).toBe(false);
  });

  it("recusa a taxa vazia num grupo com clientes, ou com valor num grupo sem clientes", () => {
    expect(eFatoresDeRecompra(comGrupo("primeira_nota", 1, { taxa_de_recompra: null }))).toBe(
      false,
    );
    expect(
      eFatoresDeRecompra(
        comGrupo("primeira_nota", 1, {
          clientes: 0,
          clientes_com_recompra: 0,
          taxa_de_recompra: 0,
        }),
      ),
    ).toBe(false);
  });

  it("recusa a taxa fora de 0 a 1 e a contagem que não é inteira", () => {
    expect(eFatoresDeRecompra(comGrupo("primeira_entrega", 0, { taxa_de_recompra: 1.2 }))).toBe(
      false,
    );
    expect(eFatoresDeRecompra(comGrupo("primeira_entrega", 0, { clientes: 13660.5 }))).toBe(false);
  });

  it("recusa a satisfação fora de 1 a 5, ou vazia numa faixa com avaliações", () => {
    expect(eFatoresDeRecompra(comGrupo("faixa_de_atraso", 0, { satisfacao: 5.1 }))).toBe(false);
    expect(eFatoresDeRecompra(comGrupo("faixa_de_atraso", 1, { satisfacao: null }))).toBe(false);
    expect(
      eFatoresDeRecompra(comGrupo("faixa_de_atraso", 2, { avaliacoes: 0, satisfacao: 2 })),
    ).toBe(false);
  });

  it("recusa o período sem datas ISO", () => {
    expect(
      eFatoresDeRecompra({
        ...dozeMeses(),
        periodo: { inicio: "1/12/2025", fim: "x" },
      }),
    ).toBe(false);
  });
});

describe("os fatores sem nenhum grupo com dados", () => {
  it("é o período sem cliente e sem avaliação", () => {
    const corpo = vazio();
    expect(eFatoresDeRecompra(corpo) && semGrupos(corpo)).toBe(true);
  });

  it("não é o período com algum grupo com dados", () => {
    const corpo = dozeMeses();
    expect(eFatoresDeRecompra(corpo) && semGrupos(corpo)).toBe(false);
  });
});
