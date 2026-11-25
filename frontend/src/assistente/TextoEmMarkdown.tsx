import type { ReactNode } from "react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import estilos from "./TextoEmMarkdown.module.css";

// Markdown simples: parágrafos, ênfase, listas, subtítulos e tabelas compactas (FE §8). O resto
// (links, imagens, código, tachado) vira o texto de dentro. HTML no texto aparece como texto: o
// padrão do react-markdown não o interpreta, e por isso não entram `rehype-raw` nem `skipHtml`.
// O `remark-gfm` só traz a sintaxe das tabelas; ele não liga HTML.
const ELEMENTOS_PERMITIDOS = [
  "p",
  "strong",
  "em",
  "ul",
  "ol",
  "li",
  "br",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "table",
  "thead",
  "tbody",
  "tr",
  "th",
  "td",
];

/** Todo título da resposta vira `h4`: ela vive abaixo do `h2` do painel e do `h3` das visões. */
function Subtitulo({ children }: { children?: ReactNode }) {
  return <h4>{children}</h4>;
}

const COMPONENTES: Components = {
  h1: Subtitulo,
  h2: Subtitulo,
  h3: Subtitulo,
  h4: Subtitulo,
  h5: Subtitulo,
  h6: Subtitulo,
  // A tabela larga rola dentro da própria caixa, sem alargar o painel lateral (FE §11).
  table: ({ children }) => (
    <div className={estilos.rolagem}>
      <table>{children}</table>
    </div>
  ),
};

/** O texto da resposta do assistente, desenhado em Markdown simples. */
export function TextoEmMarkdown({ texto }: { texto: string }) {
  return (
    <div className={estilos.texto}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        allowedElements={ELEMENTOS_PERMITIDOS}
        unwrapDisallowed
        components={COMPONENTES}
      >
        {texto}
      </Markdown>
    </div>
  );
}
