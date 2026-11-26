import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  BlocoDeDesempenhoDosCanais,
  TabelaDeDesempenhoDosCanais,
} from "./BlocoDeDesempenhoDosCanais";
import type { DesempenhoDoCanal } from "./desempenhoDosCanais";

/** Os canais de 30 dias, na ordem da API, com um canal sem fechamento e um sem lead. */
const CANAIS: DesempenhoDoCanal[] = [
  { canal: "Indicação", leads: 10, novos_lojistas: 3, conversao: 0.3, dias_ate_fechar: 41.667 },
  { canal: "Mídia paga", leads: 16, novos_lojistas: 4, conversao: 0.25, dias_ate_fechar: 1 },
  { canal: "Orgânico", leads: 1900, novos_lojistas: 2, conversao: 2 / 1900, dias_ate_fechar: 50 },
  { canal: "Prospecção ativa", leads: 12, novos_lojistas: 0, conversao: 0, dias_ate_fechar: null },
  { canal: "Eventos", leads: 0, novos_lojistas: 1, conversao: null, dias_ate_fechar: 62 },
];

/** As células de cada linha do corpo da tabela, em texto. */
function linhas(html: string): string[][] {
  const corpo = html.split("<tbody>")[1]?.split("</tbody>")[0] ?? "";
  return corpo
    .split("<tr>")
    .slice(1)
    .map((linha) => [...linha.matchAll(/<td[^>]*>(.*?)<\/td>/g)].map((celula) => celula[1] ?? ""));
}

/** As células da linha de um canal. */
function linhaDo(html: string, canal: string): string[] {
  const linha = linhas(html).find((celulas) => celulas[0] === canal);
  if (!linha) throw new Error(`sem a linha do canal ${canal}`);
  return linha;
}

describe("tabela de desempenho dos canais", () => {
  const html = renderToStaticMarkup(<TabelaDeDesempenhoDosCanais canais={CANAIS} />);

  it("tem as colunas canal, leads, novos lojistas, conversão e dias até fechar", () => {
    const titulos = [...html.matchAll(/<th[^>]*>([^<]+)<\/th>/g)].map((th) => th[1]);

    expect(titulos).toEqual(["Canal", "Leads", "Novos lojistas", "Conversão", "Dias até fechar"]);
  });

  it("mostra os cinco canais na ordem em que a API os devolve", () => {
    expect(linhas(html).map((celulas) => celulas[0])).toEqual([
      "Indicação",
      "Mídia paga",
      "Orgânico",
      "Prospecção ativa",
      "Eventos",
    ]);
  });

  it("formata as contagens, a conversão em percentual e os dias arredondados", () => {
    const indicacao = linhaDo(html, "Indicação");
    const organico = linhaDo(html, "Orgânico");

    expect(indicacao.slice(1)).toEqual(["10", "3", "30,0%", "42"]);
    expect(organico.slice(1)).toEqual(["1.900", "2", "0,1%", "50"]);
  });

  it("o canal sem fechamento fica com os dias vazios, e a linha continua inteira", () => {
    const prospeccao = linhaDo(html, "Prospecção ativa");

    expect(prospeccao).toHaveLength(5);
    expect(prospeccao[3]).toBe("0,0%");
    expect(prospeccao[4]).toContain("—");
    expect(prospeccao[4]).toContain("Nenhum lead fechou no período");
  });

  it("o canal sem lead fica com a conversão vazia, e a linha continua inteira", () => {
    const eventos = linhaDo(html, "Eventos");

    expect(eventos).toHaveLength(5);
    expect(eventos.slice(1, 3)).toEqual(["0", "1"]);
    expect(eventos[3]).toContain("—");
    expect(eventos[3]).toContain("Sem leads no período");
    expect(eventos[4]).toBe("62");
  });

  it("tem nome para leitores de tela e rola dentro da própria moldura", () => {
    expect(html).toMatch(/role="region"[^>]*aria-label="Desempenho dos canais no período"/);
    expect(html).toContain("<caption");
  });

  it("diz canal, nunca origem", () => {
    expect(html.toLowerCase()).not.toContain("origem");
  });
});

describe("o bloco de desempenho dos canais com a resposta pronta", () => {
  function bloco(canais: DesempenhoDoCanal[]): string {
    const dados = { periodo: { inicio: "2026-11-01", fim: "2026-11-30" }, canais };
    return renderToStaticMarkup(
      <BlocoDeDesempenhoDosCanais estado={{ fase: "pronto", dados }} tentarDeNovo={() => {}} />,
    );
  }
  const semMovimento = CANAIS.map(
    (item): DesempenhoDoCanal => ({
      canal: item.canal,
      leads: 0,
      novos_lojistas: 0,
      conversao: null,
      dias_ate_fechar: null,
    }),
  );

  it("num período sem lead e sem novo lojista em nenhum canal, mostra o estado vazio", () => {
    const html = bloco(semMovimento);

    expect(html).toContain("Nenhum lead nem novo lojista no período");
    expect(html).toContain("Escolha um período maior");
    expect(html).not.toContain("<table");
  });

  it("com um único novo lojista e nenhum lead, a tabela continua com os cinco canais", () => {
    const html = bloco(
      semMovimento.map((item) =>
        item.canal === "Eventos" ? { ...item, novos_lojistas: 1, dias_ate_fechar: 62 } : item,
      ),
    );

    expect(html).not.toContain("Nenhum lead nem novo lojista");
    expect(linhas(html)).toHaveLength(5);
  });

  it("com leads e nenhum novo lojista, a tabela continua com os cinco canais", () => {
    const html = bloco(
      semMovimento.map((item) =>
        item.canal === "Orgânico" ? { ...item, leads: 2, conversao: 0 } : item,
      ),
    );

    expect(html).not.toContain("Nenhum lead nem novo lojista");
    expect(linhas(html)).toHaveLength(5);
  });
});

describe("o bloco de desempenho dos canais enquanto carrega", () => {
  const html = renderToStaticMarkup(
    <BlocoDeDesempenhoDosCanais estado={{ fase: "carregando" }} tentarDeNovo={() => {}} />,
  );

  it("mantém a moldura com o título e anuncia o carregamento", () => {
    expect(html).toContain("Desempenho dos canais");
    expect(html).toContain('aria-busy="true"');
    expect(html).toMatch(/role="status"[^>]*>.*Carregando o desempenho dos canais…/);
  });
});
