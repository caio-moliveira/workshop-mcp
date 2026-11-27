import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BlocoDeTendencia, GraficosDaTendencia } from "./BlocoDeTendencia";
import { INDICADORES, linhasDaDica } from "./indicadoresDaTendencia";
import type { PontoDaTendencia, TendenciaDaDiretoria } from "./tendencia";

function ponto(troca: Partial<PontoDaTendencia> = {}): PontoDaTendencia {
  return {
    inicio: "2026-11-23",
    receita: 70663.29,
    taxa_de_recompra: 13 / 67,
    clientes: 67,
    clientes_com_recompra: 13,
    satisfacao: 3.6444,
    avaliacoes: 45,
    taxa_de_atraso: 2 / 52,
    entregues: 52,
    atrasos: 2,
    ...troca,
  };
}

/** Dois dias de 30 dias: o último ainda sem nenhum pedido entregue. */
function trintaDias(): TendenciaDaDiretoria {
  return {
    periodo: { inicio: "2026-11-01", fim: "2026-11-30" },
    agrupamento: "dia",
    pontos: [
      ponto(),
      ponto({ inicio: "2026-11-30", taxa_de_atraso: null, entregues: 0, atrasos: 0 }),
    ],
  };
}

function indicador(rotulo: string) {
  const achado = INDICADORES.find((item) => item.rotulo === rotulo);
  if (!achado) throw new Error(rotulo);
  return achado;
}

describe("os gráficos pequenos da tendência", () => {
  const html = renderToStaticMarkup(<GraficosDaTendencia dados={trintaDias()} />);

  it("mostra a tendência num bloco com título acessível e a granularidade", () => {
    expect(html).toMatch(/<section[^>]*aria-labelledby=/);
    expect(html).toContain("Tendência dos indicadores");
    expect(html).toContain("Por dia");
  });

  it("tem os quatro gráficos, cada um com o seu rótulo, na ordem do painel", () => {
    const rotulos = [...html.matchAll(/<h3[^>]*>([^<]+)<\/h3>/g)].map((achado) => achado[1]);

    expect(rotulos).toEqual(["Receita", "Taxa de recompra", "Satisfação", "Taxa de atraso"]);
  });

  it("cada gráfico é uma figura rotulada pelo próprio título", () => {
    expect(html.match(/<figure[^>]*aria-labelledby=/g)).toHaveLength(4);
  });

  it("descreve cada série em texto para os leitores de tela, com o ponto vazio dito como tal", () => {
    expect(html).toContain(
      "Taxa de atraso por dia: 23/11/2026, 3,8%; 30/11/2026, sem pedido entregue.",
    );
    expect(html).toContain("Receita por dia: 23/11/2026, R$");
  });

  it("diz semana e mês por extenso nos outros agrupamentos", () => {
    const mensal = renderToStaticMarkup(
      <GraficosDaTendencia
        dados={{ ...trintaDias(), agrupamento: "mes", pontos: [ponto({ inicio: "2025-12-01" })] }}
      />,
    );

    expect(mensal).toContain("Por mês");
    expect(mensal).toContain("Satisfação por mês: Dezembro de 2025, 3,64.");
  });
});

describe("a dica de um ponto da tendência", () => {
  it("traz o valor do ponto e a base de que ele saiu", () => {
    const receita = linhasDaDica(indicador("Receita"), ponto());
    expect(receita).toHaveLength(1);
    expect(receita[0]?.valor).toMatch(/^R\$\s70\.663,29$/);
    expect(linhasDaDica(indicador("Taxa de recompra"), ponto())).toMatchObject([
      { rotulo: "Taxa de recompra", valor: "19,4%" },
      { rotulo: "Clientes com recompra", valor: "13 de 67" },
    ]);
    expect(linhasDaDica(indicador("Satisfação"), ponto())).toMatchObject([
      { rotulo: "Nota média", valor: "3,64" },
      { rotulo: "Avaliações", valor: "45" },
    ]);
    expect(linhasDaDica(indicador("Taxa de atraso"), ponto())).toMatchObject([
      { rotulo: "Taxa de atraso", valor: "3,8%" },
      { rotulo: "Entregues com atraso", valor: "2 de 52" },
    ]);
  });

  it("no ponto sem entrega, a taxa de atraso fica vazia", () => {
    const linhas = linhasDaDica(
      indicador("Taxa de atraso"),
      ponto({ taxa_de_atraso: null, entregues: 0, atrasos: 0 }),
    );

    expect(linhas.map((l) => l.valor)).toEqual(["—", "0 de 0"]);
  });

  it("no ponto sem avaliação, a satisfação fica vazia", () => {
    const linhas = linhasDaDica(indicador("Satisfação"), ponto({ satisfacao: null, avaliacoes: 0 }));

    expect(linhas.map((l) => l.valor)).toEqual(["—", "0"]);
  });
});

describe("o bloco da tendência", () => {
  it("sem nenhum cliente no período, mostra o estado vazio no lugar dos gráficos", () => {
    const vazio = ponto({
      receita: 0,
      clientes: 0,
      clientes_com_recompra: 0,
      taxa_de_recompra: null,
    });
    const html = renderToStaticMarkup(
      <GraficosDaTendencia dados={{ ...trintaDias(), pontos: [vazio, vazio] }} />,
    );

    expect(html).toContain("Nenhum pedido aprovado no período");
    expect(html).not.toContain("<figure");
  });

  it("anuncia o carregamento aos leitores de tela", () => {
    const fonte = { consultar: () => new Promise<never>(() => {}) };
    const html = renderToStaticMarkup(<BlocoDeTendencia fonte={fonte} periodo="30d" />);

    expect(html).toMatch(/role="status"[^>]*>.*Carregando a tendência dos indicadores…/);
  });
});
