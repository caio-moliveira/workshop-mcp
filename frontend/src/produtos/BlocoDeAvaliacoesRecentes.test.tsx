import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { AvaliacaoRecente } from "./avaliacoesRecentes";
import { TabelaDeAvaliacoesRecentes } from "./BlocoDeAvaliacoesRecentes";

function avaliacao(comentario: string | null): AvaliacaoRecente {
  return {
    produto: 1,
    nome_do_produto: "Câmera de segurança Pro",
    categoria: "Eletrônicos",
    nota: 5,
    data: "2024-12-10",
    comentario,
  };
}

function desenhar(...avaliacoes: AvaliacaoRecente[]): string {
  return renderToStaticMarkup(<TabelaDeAvaliacoesRecentes avaliacoes={avaliacoes} />);
}

describe("tabela de avaliações recentes", () => {
  it("mostra produto, categoria, nota, data e comentário", () => {
    const html = desenhar(avaliacao("Chegou antes do prazo."));

    for (const coluna of ["Produto", "Categoria", "Nota", "Data", "Comentário"]) {
      expect(html).toContain(`>${coluna}</th>`);
    }
    expect(html).toContain("Câmera de segurança Pro");
    expect(html).toContain("Eletrônicos");
    expect(html).toContain("10/12/2024");
    expect(html).toContain("Chegou antes do prazo.");
  });

  it("mostra o comentário como texto simples, sem interpretar HTML nem Markdown", () => {
    const html = desenhar(avaliacao('**Ótimo** <b>produto</b> <script>alert("x")</script>'));

    expect(html).not.toContain("<b>");
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<strong>");
    expect(html).toContain("**Ótimo** &lt;b&gt;produto&lt;/b&gt; &lt;script&gt;");
  });

  it("a avaliação sem comentário fica sem texto, sem quebrar a linha", () => {
    const html = desenhar(avaliacao(null), avaliacao("Bom."));

    expect(html.match(/<tr>/g)).toHaveLength(3);
    expect(html).toContain("Sem comentário");
    expect(html).not.toContain("null");
  });
});
