import Markdown from "react-markdown";

import estilos from "./TextoEmMarkdown.module.css";

// Markdown simples: parágrafos, ênfase e listas. O resto (títulos, links, imagens, código) vira o
// texto de dentro. HTML no texto aparece como texto: o padrão do react-markdown não o interpreta, e
// por isso não entram `rehype-raw` nem `skipHtml`.
const ELEMENTOS_PERMITIDOS = ["p", "strong", "em", "ul", "ol", "li", "br"];

/** O texto da resposta do assistente, desenhado em Markdown simples. */
export function TextoEmMarkdown({ texto }: { texto: string }) {
  return (
    <div className={estilos.texto}>
      <Markdown allowedElements={ELEMENTOS_PERMITIDOS} unwrapDisallowed>
        {texto}
      </Markdown>
    </div>
  );
}
