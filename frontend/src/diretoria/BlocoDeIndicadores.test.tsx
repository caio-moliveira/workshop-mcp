import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CartoesDeIndicadores } from "./BlocoDeIndicadores";
import type { IndicadoresDaDiretoria } from "./indicadores";

function trintaDias(): IndicadoresDaDiretoria {
  return {
    periodo: { inicio: "2026-11-01", fim: "2026-11-30" },
    receita: { atual: 2_405_996.39, anterior: 2_000_000 },
    taxa_de_recompra: {
      atual: 308 / 2173,
      anterior: 0.13,
      clientes_com_recompra: 308,
      clientes: 2173,
    },
    satisfacao: { atual: 4.1229, anterior: 4.0698, avaliacoes: 1237 },
    retencao: { atual: 0.0086, anterior: 0.007, retidos: 11, clientes_do_periodo_anterior: 1296 },
  };
}

/** O HTML de cada cartão, pelo rótulo. */
function cartoes(html: string): Record<string, string> {
  const porRotulo: Record<string, string> = {};
  for (const cartao of html.split("<article").slice(1)) {
    const rotulo = /<h3[^>]*>([^<]+)<\/h3>/.exec(cartao)?.[1];
    if (rotulo) porRotulo[rotulo] = cartao;
  }
  return porRotulo;
}

describe("cartões da Diretoria em 30 dias", () => {
  const porRotulo = cartoes(
    renderToStaticMarkup(<CartoesDeIndicadores dados={trintaDias()} periodo="30d" />),
  );

  it("mostra os quatro cartões, na ordem do painel", () => {
    expect(Object.keys(porRotulo)).toEqual([
      "Receita",
      "Taxa de recompra",
      "Satisfação",
      "Retenção",
    ]);
  });

  it("Receita varia em percentual", () => {
    expect(porRotulo["Receita"]).toContain("2.405.996,39");
    expect(porRotulo["Receita"]).toContain("+20,3%");
  });

  it("Taxa de recompra traz, na legenda, os clientes com recompra e os que compraram", () => {
    expect(porRotulo["Taxa de recompra"]).toContain(">14,2%<");
    expect(porRotulo["Taxa de recompra"]).toContain("308 de 2.173 clientes compraram de novo");
    expect(porRotulo["Taxa de recompra"]).toContain("+1,2 p.p.");
  });

  it("Satisfação é a nota média e varia em pontos de nota", () => {
    expect(porRotulo["Satisfação"]).toContain(">4,12<");
    expect(porRotulo["Satisfação"]).toContain("Nota média de 1.237 avaliações");
    expect(porRotulo["Satisfação"]).toContain("+0,05");
    expect(porRotulo["Satisfação"]).not.toContain("p.p.");
  });

  it("Retenção traz, na legenda, os clientes do período anterior que compraram de novo", () => {
    expect(porRotulo["Retenção"]).toContain(">0,9%<");
    expect(porRotulo["Retenção"]).toContain(
      "11 de 1.296 clientes do período anterior compraram de novo",
    );
    expect(porRotulo["Retenção"]).toContain("+0,2 p.p.");
  });

  it("os quatro cartões comparam com o período anterior, e subir é bom em todos", () => {
    for (const rotulo of Object.keys(porRotulo)) {
      expect(porRotulo[rotulo]).toContain("em relação aos 30 dias anteriores");
    }
  });
});

describe("cartões da Diretoria em 12 meses", () => {
  const dados = trintaDias();
  dados.retencao = {
    atual: 573 / 12495,
    anterior: null,
    retidos: 573,
    clientes_do_periodo_anterior: 12495,
  };
  const porRotulo = cartoes(
    renderToStaticMarkup(<CartoesDeIndicadores dados={dados} periodo="12m" />),
  );

  it("a retenção tem valor e não tem variação", () => {
    expect(porRotulo["Retenção"]).toContain(">4,6%<");
    expect(porRotulo["Retenção"]).not.toContain("em relação");
  });

  it("os outros três cartões continuam com variação", () => {
    for (const rotulo of ["Receita", "Taxa de recompra", "Satisfação"]) {
      expect(porRotulo[rotulo]).toContain("em relação aos 12 meses anteriores");
    }
  });
});

describe("cartões da Diretoria em 24 meses", () => {
  const dados: IndicadoresDaDiretoria = {
    periodo: { inicio: "2024-12-01", fim: "2026-11-30" },
    receita: { atual: 30_625_969.36, anterior: null },
    taxa_de_recompra: {
      atual: 1365 / 27301,
      anterior: null,
      clientes_com_recompra: 1365,
      clientes: 27301,
    },
    satisfacao: { atual: 4.0882, anterior: null, avaliacoes: 20114 },
    retencao: { atual: null, anterior: null, retidos: null, clientes_do_periodo_anterior: null },
  };
  const html = renderToStaticMarkup(<CartoesDeIndicadores dados={dados} periodo="24m" />);
  const porRotulo = cartoes(html);

  it("nenhum cartão tem variação", () => {
    expect(html).not.toContain("em relação");
    expect(html).not.toContain("p.p.");
  });

  it("a retenção mostra — e diz que não há período anterior nos dados", () => {
    expect(porRotulo["Retenção"]).toContain(">—<");
    expect(porRotulo["Retenção"]).toContain("Sem período anterior nos dados");
  });
});

describe("cartões da Diretoria num período sem cliente e sem avaliação", () => {
  const dados = trintaDias();
  dados.receita = { atual: 0, anterior: 1000 };
  dados.taxa_de_recompra = { atual: null, anterior: 0.1, clientes_com_recompra: 0, clientes: 0 };
  dados.satisfacao = { atual: null, anterior: 4, avaliacoes: 0 };
  const porRotulo = cartoes(
    renderToStaticMarkup(<CartoesDeIndicadores dados={dados} periodo="30d" />),
  );

  it("os quatro cartões continuam aparecendo", () => {
    expect(Object.keys(porRotulo)).toHaveLength(4);
  });

  it("taxa de recompra e satisfação ficam sem valor e dizem por quê", () => {
    expect(porRotulo["Taxa de recompra"]).toContain(">—<");
    expect(porRotulo["Taxa de recompra"]).toContain("Sem clientes no período");
    expect(porRotulo["Satisfação"]).toContain(">—<");
    expect(porRotulo["Satisfação"]).toContain("Sem avaliações no período");
  });
});
