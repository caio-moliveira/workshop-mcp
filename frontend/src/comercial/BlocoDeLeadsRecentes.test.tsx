import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { TabelaDeLeadsRecentes } from "./BlocoDeLeadsRecentes";
import type { LeadRecente } from "./leadsRecentes";

function emProposta(): LeadRecente {
  return {
    lead: 1500,
    empresa: "Comércio Aurora Ltda",
    canal: "Indicação",
    etapa: "Proposta",
    data_criacao: "2026-10-05",
    data_fechamento: null,
  };
}

function fechado(): LeadRecente {
  return {
    lead: 1499,
    empresa: "Casa Horizonte ME",
    canal: "Mídia paga",
    etapa: "Fechado",
    data_criacao: "2026-09-12",
    data_fechamento: "2026-11-03",
  };
}

function desenhar(...leads: LeadRecente[]): string {
  return renderToStaticMarkup(<TabelaDeLeadsRecentes leads={leads} />);
}

/** O HTML de cada linha do corpo da tabela. */
function linhas(html: string): string[] {
  return (html.split("<tbody>")[1] ?? "").split("<tr>").slice(1);
}

describe("tabela de leads recentes", () => {
  it("mostra empresa, canal, etapa, criação e fechamento, nesta ordem", () => {
    const html = desenhar(fechado());

    const titulos = [...html.matchAll(/<th[^>]*>([^<]+)<\/th>/g)].map((th) => th[1]);
    expect(titulos).toEqual(["Empresa", "Canal", "Etapa", "Criação", "Fechamento"]);
    expect(html).toContain("Casa Horizonte ME");
    expect(html).toContain("Mídia paga");
    expect(html).toContain("Fechado");
    expect(html).toContain("12/09/2026");
    expect(html).toContain("03/11/2026");
  });

  it("o lead que não fechou fica com o fechamento vazio, sem quebrar a linha", () => {
    const html = desenhar(emProposta(), fechado());

    const [semFechamento = "", comFechamento = "", ...outras] = linhas(html);
    expect(outras).toHaveLength(0);
    expect(semFechamento.match(/<td/g)).toHaveLength(5);
    expect(comFechamento.match(/<td/g)).toHaveLength(5);
    expect(semFechamento).toContain("Sem fechamento");
    expect(comFechamento).not.toContain("Sem fechamento");
    expect(html).not.toContain("null");
  });

  it("mantém a ordem recebida, do lead mais recente para o mais antigo", () => {
    const html = desenhar(emProposta(), fechado());

    expect(html.indexOf("Comércio Aurora Ltda")).toBeLessThan(html.indexOf("Casa Horizonte ME"));
  });

  it("diz canal, nunca origem", () => {
    expect(desenhar(emProposta()).toLowerCase()).not.toContain("origem");
  });

  it("fica numa área de rolagem com nome, para rolar na horizontal em tela pequena", () => {
    const html = desenhar(emProposta());

    expect(html).toMatch(/<div[^>]*role="region"[^>]*aria-label="Leads recentes do período"/);
  });
});
