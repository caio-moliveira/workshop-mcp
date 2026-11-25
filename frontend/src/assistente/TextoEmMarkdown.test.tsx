import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { TextoEmMarkdown } from "./TextoEmMarkdown";

function desenhar(texto: string): string {
  return renderToStaticMarkup(<TextoEmMarkdown texto={texto} />);
}

describe("texto da resposta em Markdown", () => {
  it("desenha parágrafos, negrito e listas", () => {
    const html = desenhar("Os atrasos vêm de **três lojistas**:\n\n- Loja A\n- Loja B");
    expect(html).toContain("<p>Os atrasos vêm de <strong>três lojistas</strong>:</p>");
    expect(html).toContain("<ul>\n<li>Loja A</li>\n<li>Loja B</li>\n</ul>");
  });

  it("mostra o HTML do texto como texto, sem interpretá-lo", () => {
    const html = desenhar('Veja <b>isto</b> <script>alert("x")</script>');
    expect(html).not.toContain("<b>");
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;b&gt;isto&lt;/b&gt;");
    expect(html).toContain("&lt;script&gt;");
  });

  it("um link vira só o texto dele", () => {
    const html = desenhar("[clique](javascript:alert(1))");
    expect(html).not.toContain("<a");
    expect(html).toContain("clique");
  });

  it("desenha uma tabela de comparação, dentro de uma área que rola na horizontal", () => {
    const html = desenhar(
      ["| Rota | Atraso |", "| --- | ---: |", "| SP → RJ | 12% |", "| SP → BH | 8% |"].join("\n"),
    );
    expect(html).toMatch(/<div[^>]*class="[^"]*rolagem[^"]*"[^>]*><table>/);
    expect(html).toContain("<th>Rota</th>");
    expect(html).toContain('<th style="text-align:right">Atraso</th>');
    expect(html).toContain("<td>SP → RJ</td>");
    expect(html).toContain('<td style="text-align:right">12%</td>');
  });

  it("um subtítulo vira um título de nível baixo, abaixo do título do painel", () => {
    const html = desenhar("# Resumo\n\n## Por rota\n\nTexto.");
    expect(html).toContain("<h4>Resumo</h4>");
    expect(html).toContain("<h4>Por rota</h4>");
    expect(html).not.toMatch(/<h[1-3]/);
  });

  it("o HTML dentro de uma célula da tabela continua como texto", () => {
    const html = desenhar(["| A |", "| --- |", "| <img src=x onerror=alert(1)> |"].join("\n"));
    expect(html).toContain("<td>");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;img");
  });
});
