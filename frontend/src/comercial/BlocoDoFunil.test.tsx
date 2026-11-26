import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BlocoDoFunil, GraficoDoFunil } from "./BlocoDoFunil";
import type { FunilDoComercial } from "./funil";

/** Os 12 meses dos dados atuais, com Fechado aumentado para passar do milhar. */
const DADOS: FunilDoComercial = {
  periodo: { inicio: "2025-12-01", fim: "2026-11-30" },
  etapas: [
    { etapa: "Novo", leads: 76 },
    { etapa: "Contatado", leads: 38 },
    { etapa: "Qualificado", leads: 40 },
    { etapa: "Proposta", leads: 27 },
    { etapa: "Fechado", leads: 1110 },
    { etapa: "Perdido", leads: 455 },
  ],
};

describe("gráfico do funil", () => {
  const html = renderToStaticMarkup(<GraficoDoFunil dados={DADOS} />);

  it("tem o título do bloco e diz que a etapa é a atual", () => {
    expect(html).toContain(">Leads por etapa do funil<");
    expect(html).toContain("etapa atual");
  });

  it("a legenda separa as etapas do funil de Perdido", () => {
    const legenda = /<ul[^>]*>(.*?)<\/ul>/.exec(html)?.[1] ?? "";

    expect(legenda.indexOf("Etapas do funil")).toBeGreaterThan(-1);
    expect(legenda.indexOf("Perdido")).toBeGreaterThan(legenda.indexOf("Etapas do funil"));
  });

  it("descreve as barras em texto, na ordem do funil e com Perdido à parte", () => {
    expect(html).toContain(
      "Leads criados no período, pela etapa atual: Novo, 76; Contatado, 38; Qualificado, 40; " +
        "Proposta, 27; Fechado, 1.110. À parte, Perdido, 455.",
    );
  });
});

describe("bloco do funil antes de a rota responder", () => {
  const fonte = { consultar: () => new Promise<never>(() => {}) };
  const html = renderToStaticMarkup(<BlocoDoFunil fonte={fonte} periodo="12m" />);

  it("anuncia o carregamento aos leitores de tela, sem o gráfico", () => {
    expect(html).toContain('role="status"');
    expect(html).toContain("Carregando os leads por etapa do funil…");
    expect(html).not.toContain(">Leads por etapa do funil<");
  });
});
