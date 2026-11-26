import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BlocoDosFatoresDeRecompra, FatoresDeRecompraEmBlocos } from "./BlocoDosFatoresDeRecompra";
import { linhasDaDicaDeRecompra, linhasDaDicaDeSatisfacao } from "./dicaDosFatores";
import type { FatoresDeRecompra, GrupoDeRecompra } from "./fatores";

const COM_ATRASO_VAZIO: GrupoDeRecompra<"Com atraso"> = {
  grupo: "Com atraso",
  clientes: 0,
  clientes_com_recompra: 0,
  taxa_de_recompra: null,
};
const NO_PRAZO: GrupoDeRecompra<"No prazo"> = {
  grupo: "No prazo",
  clientes: 13660,
  clientes_com_recompra: 1204,
  taxa_de_recompra: 1204 / 13660,
};

/** Os 12 meses dos dados atuais. */
const DOZE_MESES: FatoresDeRecompra = {
  periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
  primeira_entrega: [
    NO_PRAZO,
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

const VAZIO: FatoresDeRecompra = {
  ...DOZE_MESES,
  primeira_entrega: DOZE_MESES.primeira_entrega.map((item) => ({
    ...item,
    clientes: 0,
    clientes_com_recompra: 0,
    taxa_de_recompra: null,
  })),
  primeira_nota: DOZE_MESES.primeira_nota.map((item) => ({
    ...item,
    clientes: 0,
    clientes_com_recompra: 0,
    taxa_de_recompra: null,
  })),
  faixa_de_atraso: DOZE_MESES.faixa_de_atraso.map((item) => ({
    ...item,
    avaliacoes: 0,
    satisfacao: null,
  })),
};

describe("as dicas dos fatores de recompra", () => {
  it("num grupo de recompra, trazem a taxa e o tamanho do grupo", () => {
    const linhas = linhasDaDicaDeRecompra({
      grupo: "4 ou 5",
      clientes: 8408,
      clientes_com_recompra: 1087,
      taxa_de_recompra: 1087 / 8408,
    });

    expect(linhas.map(({ rotulo, valor }) => [rotulo, valor])).toEqual([
      ["Taxa de recompra", "12,9%"],
      ["Clientes com recompra", "1.087"],
      ["Clientes do grupo", "8.408"],
    ]);
  });

  it("num grupo sem clientes, a taxa fica vazia", () => {
    const linhas = linhasDaDicaDeRecompra(COM_ATRASO_VAZIO);

    expect(linhas.map(({ valor }) => valor)).toEqual(["—", "0", "0"]);
  });

  it("numa faixa de atraso, trazem a satisfação e as avaliações do grupo", () => {
    const linhas = linhasDaDicaDeSatisfacao({
      grupo: "Até 7 dias",
      avaliacoes: 533,
      satisfacao: 2.8311,
    });

    expect(linhas.map(({ rotulo, valor }) => [rotulo, valor])).toEqual([
      ["Satisfação", "2,83"],
      ["Avaliações do grupo", "533"],
    ]);
  });
});

describe("os três blocos dos fatores de recompra", () => {
  const html = renderToStaticMarkup(<FatoresDeRecompraEmBlocos dados={DOZE_MESES} />);

  it("mostram os três gráficos, cada um com título acessível", () => {
    expect(html.match(/<section[^>]*aria-labelledby=/g)).toHaveLength(3);
    expect(html).toContain(">Recompra pela primeira entrega<");
    expect(html).toContain(">Recompra pela primeira nota<");
    expect(html).toContain(">Satisfação pela faixa de atraso<");
  });

  it("dizem quais grupos ficam de fora", () => {
    expect(html).toContain("em trânsito ou com prazo vencido ficam de fora");
    expect(html).toContain("Quem não o avaliou fica de fora");
  });

  it("descrevem as barras em texto, para quem não vê o gráfico", () => {
    expect(html).toContain(
      "Taxa de recompra dos clientes do período, pela entrega do primeiro pedido: No prazo, 8,8%; Com atraso, 0,0%.",
    );
    expect(html).toContain(
      "Taxa de recompra dos clientes do período, pela nota do primeiro pedido: 1 ou 2, 0,8%; 3, 10,2%; 4 ou 5, 12,9%.",
    );
    expect(html).toContain(
      "Satisfação das avaliações do período, pela faixa de atraso da entrega: No prazo, 4,28; Até 7 dias, 2,83; Mais de 7 dias, 1,75.",
    );
  });

  it("num período sem cliente e sem avaliação, mostram o estado vazio no lugar das barras", () => {
    const vazio = renderToStaticMarkup(<FatoresDeRecompraEmBlocos dados={VAZIO} />);

    expect(vazio).toContain("Nenhum cliente nem avaliação no período");
    expect(vazio).not.toContain("recharts");
  });

  it("um grupo vazio aparece como traço, não como zero", () => {
    const comGrupoVazio: FatoresDeRecompra = {
      ...DOZE_MESES,
      primeira_entrega: [NO_PRAZO, COM_ATRASO_VAZIO],
    };
    const desenhado = renderToStaticMarkup(<FatoresDeRecompraEmBlocos dados={comGrupoVazio} />);

    expect(desenhado).toContain("No prazo, 8,8%; Com atraso, —.");
  });
});

describe("o bloco dos fatores de recompra antes de a rota responder", () => {
  const fonte = { consultar: () => new Promise<never>(() => {}) };
  const html = renderToStaticMarkup(<BlocoDosFatoresDeRecompra fonte={fonte} periodo="12m" />);

  it("anuncia o carregamento aos leitores de tela, sem os gráficos", () => {
    expect(html).toMatch(/role="status"[^>]*>.*Carregando os fatores de recompra…/);
    expect(html).not.toContain(">Recompra pela primeira entrega<");
  });
});
