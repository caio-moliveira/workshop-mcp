import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BlocoDoResumoPorCanal, TabelaDoResumoPorCanal } from "./BlocoDoResumoPorCanal";
import type { ResumoDoCanal } from "./resumo";

function canal(
  nome: ResumoDoCanal["canal"],
  pedidos: number,
  receita: number,
  [atrasos, entregues]: [number, number],
  [satisfacao, avaliacoes]: [number | null, number],
  [comRecompra, clientes]: [number, number],
): ResumoDoCanal {
  return {
    canal: nome,
    pedidos,
    receita,
    taxa_de_atraso: entregues === 0 ? null : atrasos / entregues,
    entregues,
    atrasos,
    satisfacao,
    avaliacoes,
    taxa_de_recompra: clientes === 0 ? null : comRecompra / clientes,
    clientes,
    clientes_com_recompra: comRecompra,
  };
}

/** Os canais de 12 meses, na ordem da API, com um canal sem entrega e sem avaliação no fim. */
const CANAIS: ResumoDoCanal[] = [
  canal("Mídia paga", 9214, 8_836_743.17, [1094, 8569], [4.0169, 6450], [663, 8443]),
  canal("Prospecção ativa", 1510, 2_051_376.6, [89, 1384], [4.1527, 1022], [100, 1380]),
  canal("Orgânico", 3448, 4_122_211.99, [161, 3212], [4.161, 2342], [242, 3150]),
  canal("Indicação", 1686, 1_290_924.75, [41, 1576], [4.2574, 1154], [127, 1554]),
  canal("Eventos", 12, 9_800, [0, 0], [null, 0], [0, 12]),
];

/** As células de cada linha do corpo da tabela, em texto. */
function linhas(html: string): string[][] {
  const corpo = html.split("<tbody>")[1]?.split("</tbody>")[0] ?? "";
  return corpo
    .split("<tr>")
    .slice(1)
    .map((linha) => [...linha.matchAll(/<td[^>]*>(.*?)<\/td>/g)].map((celula) => celula[1] ?? ""));
}

function linhaDo(html: string, nome: string): string[] {
  const linha = linhas(html).find((celulas) => celulas[0] === nome);
  if (!linha) throw new Error(`sem a linha do canal ${nome}`);
  return linha;
}

describe("tabela do resumo por canal", () => {
  const html = renderToStaticMarkup(<TabelaDoResumoPorCanal canais={CANAIS} />);

  it("tem as colunas canal, pedidos, receita, taxa de atraso, satisfação e taxa de recompra", () => {
    const titulos = [...html.matchAll(/<th[^>]*>([^<]+)<\/th>/g)].map((th) => th[1]);

    expect(titulos).toEqual([
      "Canal",
      "Pedidos",
      "Receita",
      "Taxa de atraso",
      "Satisfação",
      "Taxa de recompra",
    ]);
  });

  it("mostra os cinco canais na ordem em que a API os devolve", () => {
    expect(linhas(html).map((celulas) => celulas[0])).toEqual([
      "Mídia paga",
      "Prospecção ativa",
      "Orgânico",
      "Indicação",
      "Eventos",
    ]);
  });

  it("formata as contagens, a receita, as taxas em percentual e a nota com duas casas", () => {
    const [, pedidos, receita, atraso, satisfacao, recompra] = linhaDo(html, "Mídia paga");

    expect(pedidos).toBe("9.214");
    expect(receita).toMatch(/^R\$\s8\.836\.743,17$/);
    expect(atraso).toBe("12,8%");
    expect(satisfacao).toBe("4,02");
    expect(recompra).toBe("7,9%");
  });

  it("o canal sem entrega e sem avaliação fica com as taxas vazias, e a linha continua inteira", () => {
    const eventos = linhaDo(html, "Eventos");

    expect(eventos).toHaveLength(6);
    expect(eventos[1]).toBe("12");
    expect(eventos[3]).toContain("—");
    expect(eventos[3]).toContain("Nenhum pedido entregue no período");
    expect(eventos[4]).toContain("—");
    expect(eventos[4]).toContain("Nenhuma avaliação no período");
    expect(eventos[5]).toBe("0,0%");
  });

  it("tem nome para leitores de tela e rola na horizontal dentro da própria moldura", () => {
    expect(html).toMatch(/role="region"[^>]*aria-label="Resumo por canal do lojista no período"/);
    expect(html).toContain('tabindex="0"');
    expect(html).toContain("<caption");
  });

  it("diz canal, nunca origem", () => {
    expect(html.toLowerCase()).not.toContain("origem");
  });
});

describe("o bloco do resumo por canal", () => {
  function bloco(canais: ResumoDoCanal[]): string {
    const dados = { periodo: { inicio: "2025-12-01", fim: "2026-11-30" }, canais };
    return renderToStaticMarkup(
      <BlocoDoResumoPorCanal estado={{ fase: "pronto", dados }} tentarDeNovo={() => {}} />,
    );
  }

  it("com a resposta pronta, mostra o título e a tabela, dizendo canal e nunca origem", () => {
    const html = bloco(CANAIS);

    expect(html).toContain("Resumo por canal do lojista");
    expect(linhas(html)).toHaveLength(5);
    expect(html.toLowerCase()).not.toContain("origem");
  });

  it("num período sem pedido em nenhum canal, mostra o estado vazio", () => {
    const html = bloco(
      CANAIS.map((item) => canal(item.canal, 0, 0, [0, 0], [null, 0], [0, 0])),
    );

    expect(html).toContain("Nenhum pedido no período");
    expect(html).toContain("Escolha um período maior");
    expect(html).not.toContain("<table");
  });

  it("enquanto carrega, mantém a moldura com o título e anuncia o carregamento", () => {
    const html = renderToStaticMarkup(
      <BlocoDoResumoPorCanal estado={{ fase: "carregando" }} tentarDeNovo={() => {}} />,
    );

    expect(html).toContain("Resumo por canal do lojista");
    expect(html).toContain('aria-busy="true"');
    expect(html).toMatch(/role="status"[^>]*>.*Carregando o resumo por canal…/);
  });

  it("na falha, mostra o erro com a opção de tentar de novo", () => {
    const html = renderToStaticMarkup(
      <BlocoDoResumoPorCanal estado={{ fase: "erro" }} tentarDeNovo={() => {}} />,
    );

    expect(html).toContain("o resumo por canal");
    expect(html).toContain("Tentar de novo");
  });
});
