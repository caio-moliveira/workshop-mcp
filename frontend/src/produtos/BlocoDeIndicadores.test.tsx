import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CartoesDeIndicadores } from "./BlocoDeIndicadores";
import type { IndicadoresDeProdutos } from "./indicadores";

function semAvaliacoes(): IndicadoresDeProdutos {
  return {
    periodo: { inicio: "2026-11-01", fim: "2026-11-30" },
    catalogo: 2000,
    produtos_avaliados: { atual: 0, anterior: 0 },
    nota_media: { atual: null, anterior: null },
    avaliacoes: { atual: 0, anterior: 0 },
    reclamacoes: { atual: 0, anterior: 0 },
    produtos_mal_avaliados: { atual: 0, anterior: 0 },
  };
}

describe("indicadores de Produtos num período sem avaliações", () => {
  const html = renderToStaticMarkup(<CartoesDeIndicadores dados={semAvaliacoes()} periodo="30d" />);

  it("o cartão do catálogo continua aparecendo, com o tamanho do catálogo", () => {
    expect(html).toContain(">Produtos no catálogo</h3>");
    expect(html).toContain("2.000");
  });

  it("os cartões que dependem do período dizem que não há avaliações", () => {
    for (const rotulo of ["Nota média", "Produtos mal avaliados", "Avaliações recebidas"]) {
      expect(html).toContain(`>${rotulo}</h3>`);
    }
    expect(html.match(/Sem avaliações no período/g)).toHaveLength(3);
  });
});
