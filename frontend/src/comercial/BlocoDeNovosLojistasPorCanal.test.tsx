import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { FonteDeDados } from "../useBloco";
import { BlocoDeNovosLojistasPorCanal, NovosLojistasPorCanal } from "./BlocoDeNovosLojistasPorCanal";
import type { DesempenhoDoCanal } from "./desempenhoDosCanais";
import { linhasDaDica } from "./dicaDosCanais";

function canal(
  nome: DesempenhoDoCanal["canal"],
  leads: number,
  novosLojistas: number,
): DesempenhoDoCanal {
  return {
    canal: nome,
    leads,
    novos_lojistas: novosLojistas,
    conversao: leads === 0 ? null : novosLojistas / leads,
    dias_ate_fechar: novosLojistas === 0 ? null : 40,
  };
}

function cincoCanais(novosLojistas: number): DesempenhoDoCanal[] {
  return [
    canal("Indicação", 10, novosLojistas),
    canal("Mídia paga", 16, novosLojistas),
    canal("Orgânico", 19, novosLojistas),
    canal("Prospecção ativa", 12, novosLojistas),
    canal("Eventos", 10, novosLojistas),
  ];
}

describe("a dica do gráfico de novos lojistas por canal", () => {
  it("traz os novos lojistas, a conversão do canal e os leads que a acompanham", () => {
    const linhas = linhasDaDica(canal("Mídia paga", 1600, 400));

    expect(linhas.map(({ rotulo, valor }) => [rotulo, valor])).toEqual([
      ["Novos lojistas", "400"],
      ["Conversão", "25,0%"],
      ["Leads do período", "1.600"],
    ]);
  });

  it("no canal sem lead no período, a conversão fica vazia", () => {
    const linhas = linhasDaDica(canal("Eventos", 0, 1));

    expect(linhas.map(({ valor }) => valor)).toEqual(["1", "—", "0"]);
  });
});

describe("o bloco de novos lojistas por canal", () => {
  it("com novos lojistas, mostra o gráfico com título e nota acessíveis", () => {
    const html = renderToStaticMarkup(<NovosLojistasPorCanal canais={cincoCanais(3)} />);

    expect(html).toMatch(/<section[^>]*aria-labelledby=/);
    expect(html).toContain("Novos lojistas por canal");
    expect(html).toContain("conversão");
    expect(html).not.toContain("Nenhum novo lojista");
  });

  it("num período sem novo lojista, mostra o estado vazio no lugar das barras", () => {
    const html = renderToStaticMarkup(<NovosLojistasPorCanal canais={cincoCanais(0)} />);

    expect(html).toContain("Nenhum novo lojista no período");
  });

  it("diz canal, nunca origem", () => {
    const html = renderToStaticMarkup(<NovosLojistasPorCanal canais={cincoCanais(3)} />);

    expect(html.toLowerCase()).not.toContain("origem");
  });
});

describe("o bloco de novos lojistas por canal enquanto carrega", () => {
  const semResposta: FonteDeDados = { consultar: () => new Promise(() => {}) };

  it("anuncia o carregamento aos leitores de tela", () => {
    const html = renderToStaticMarkup(
      <BlocoDeNovosLojistasPorCanal fonte={semResposta} periodo="30d" />,
    );

    expect(html).toMatch(/role="status"[^>]*>.*Carregando os novos lojistas por canal…/);
  });
});
