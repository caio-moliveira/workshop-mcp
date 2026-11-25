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
});
