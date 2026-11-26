import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CartoesDeIndicadores } from "./BlocoDeIndicadores";
import type { IndicadoresDoComercial } from "./indicadores";

function dozeMeses(): IndicadoresDoComercial {
  return {
    periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
    leads: { atual: 746, anterior: 580 },
    leads_em_negociacao: 181,
    novos_lojistas: { atual: 126, anterior: 94 },
    dias_ate_fechar: 44.198,
    conversao: { atual: 126 / 746, anterior: 94 / 580 },
    principal_canal: "Mídia paga",
    parcela_do_principal_canal: 222 / 746,
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

describe("cartões do Comercial em 12 meses", () => {
  const porRotulo = cartoes(
    renderToStaticMarkup(<CartoesDeIndicadores dados={dozeMeses()} periodo="12m" />),
  );

  it("mostra os quatro cartões, na ordem do painel", () => {
    expect(Object.keys(porRotulo)).toEqual([
      "Leads",
      "Novos lojistas",
      "Conversão",
      "Principal canal",
    ]);
  });

  it("Leads traz os criados no período e, na legenda, os em negociação", () => {
    expect(porRotulo["Leads"]).toContain(">746<");
    expect(porRotulo["Leads"]).toContain("181 em negociação");
    expect(porRotulo["Leads"]).toContain("+28,6%");
  });

  it("Novos lojistas traz, na legenda, os dias médios até fechar", () => {
    expect(porRotulo["Novos lojistas"]).toContain(">126<");
    expect(porRotulo["Novos lojistas"]).toContain("44 dias até fechar, em média");
    expect(porRotulo["Novos lojistas"]).toContain("+34,0%");
  });

  it("Conversão varia em pontos percentuais e diz como é calculada", () => {
    expect(porRotulo["Conversão"]).toContain(">16,9%<");
    expect(porRotulo["Conversão"]).toContain("Novos lojistas por leads do período");
    expect(porRotulo["Conversão"]).toContain("+0,7 p.p.");
  });

  it("Principal canal mostra o nome, a parcela na legenda e nenhuma variação", () => {
    expect(porRotulo["Principal canal"]).toContain(">Mídia paga<");
    expect(porRotulo["Principal canal"]).toContain("29,8% dos leads do período");
    expect(porRotulo["Principal canal"]).not.toContain("em relação");
  });

  it("os três cartões com número comparam com o período anterior", () => {
    for (const rotulo of ["Leads", "Novos lojistas", "Conversão"]) {
      expect(porRotulo[rotulo]).toContain("em relação aos 12 meses anteriores");
    }
  });
});

describe("cartões do Comercial com mais novos lojistas do que leads no período", () => {
  const dados = dozeMeses();
  dados.leads = { atual: 4, anterior: 8 };
  dados.novos_lojistas = { atual: 6, anterior: 6 };
  dados.conversao = { atual: 1.5, anterior: 0.75 };
  const porRotulo = cartoes(
    renderToStaticMarkup(<CartoesDeIndicadores dados={dados} periodo="30d" />),
  );

  it("a conversão passa de 100% e continua formatada, com a variação em pontos percentuais", () => {
    expect(Object.keys(porRotulo)).toHaveLength(4);
    expect(porRotulo["Conversão"]).toContain(">150,0%<");
    expect(porRotulo["Conversão"]).toContain("+75,0 p.p.");
  });
});

describe("cartões do Comercial em 24 meses", () => {
  const dados = dozeMeses();
  dados.leads.anterior = null;
  dados.novos_lojistas.anterior = null;
  dados.conversao.anterior = null;
  const html = renderToStaticMarkup(<CartoesDeIndicadores dados={dados} periodo="24m" />);

  it("nenhum cartão tem variação", () => {
    expect(html).not.toContain("em relação");
    expect(html).not.toContain("p.p.");
  });
});

describe("cartões do Comercial num período sem lead e sem novo lojista", () => {
  const vazio: IndicadoresDoComercial = {
    periodo: { inicio: "2026-11-01", fim: "2026-11-30" },
    leads: { atual: 0, anterior: 4 },
    leads_em_negociacao: 0,
    novos_lojistas: { atual: 0, anterior: 1 },
    dias_ate_fechar: null,
    conversao: { atual: null, anterior: 0.25 },
    principal_canal: null,
    parcela_do_principal_canal: null,
  };
  const porRotulo = cartoes(
    renderToStaticMarkup(<CartoesDeIndicadores dados={vazio} periodo="30d" />),
  );

  it("os quatro cartões continuam aparecendo", () => {
    expect(Object.keys(porRotulo)).toHaveLength(4);
  });

  it("conversão e principal canal ficam sem valor e dizem que não há leads", () => {
    for (const rotulo of ["Conversão", "Principal canal"]) {
      expect(porRotulo[rotulo]).toContain(">—<");
      expect(porRotulo[rotulo]).toContain("Sem leads no período");
    }
  });

  it("novos lojistas diz que nenhum lead fechou, sem inventar dias", () => {
    expect(porRotulo["Novos lojistas"]).toContain(">0<");
    expect(porRotulo["Novos lojistas"]).toContain("Nenhum lead fechou no período");
  });
});
