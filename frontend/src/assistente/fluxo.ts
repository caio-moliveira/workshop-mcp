/**
 * A leitura do fluxo de eventos da rota `POST /assistente`: bytes para eventos da resposta.
 *
 * O servidor manda blocos `event: <tipo>\ndata: <JSON>\n\n`, e linhas `: ping` para manter a
 * conexão. Um bloco pode chegar partido entre pedaços, até no meio de um caractere, e um pedaço
 * pode trazer vários blocos. Nada aqui usa rede: quem traz os bytes é `rede.ts`.
 */

/** Um evento da resposta, já com os dados lidos do JSON. */
export type EventoDaResposta =
  | { tipo: "texto"; texto: string }
  | { tipo: "estado" }
  | { tipo: "fim" }
  | { tipo: "erro"; mensagem: string };

/** O fluxo acabou sem `fim` nem `erro`, ou trouxe algo fora do contrato. */
export const RESPOSTA_INTERROMPIDA = "A resposta foi interrompida. Tente de novo.";

class ForaDoContrato extends Error {}

/**
 * Lê os eventos do fluxo até o `fim` ou o `erro`, que é sempre o último. Um fluxo que acaba antes,
 * ou que traz um evento fora do contrato, termina num `erro` com `RESPOSTA_INTERROMPIDA`.
 */
export async function* lerEventos(
  pedacos: AsyncIterable<Uint8Array>,
): AsyncGenerator<EventoDaResposta> {
  const decodificador = new TextDecoder();
  let resto = "";
  try {
    for await (const pedaco of pedacos) {
      resto += decodificador.decode(pedaco, { stream: true });
      // Um "\r" no fim pode ser metade de um "\r\n" que termina no próximo pedaço.
      const pendente = resto.endsWith("\r") ? "\r" : "";
      const blocos = resto
        .slice(0, resto.length - pendente.length)
        .replace(/\r\n?/g, "\n")
        .split("\n\n");
      resto = (blocos.pop() ?? "") + pendente;
      for (const bloco of blocos) {
        const evento = lerBloco(bloco);
        if (!evento) continue;
        yield evento;
        if (evento.tipo === "fim" || evento.tipo === "erro") return;
      }
    }
  } catch (erro) {
    if (!(erro instanceof ForaDoContrato)) throw erro;
  }
  yield { tipo: "erro", mensagem: RESPOSTA_INTERROMPIDA };
}

/** Um bloco como evento da resposta, ou nada para comentário e tipo desconhecido. */
function lerBloco(bloco: string): EventoDaResposta | null {
  let tipo = "message";
  const linhasDeDados: string[] = [];
  for (const linha of bloco.split("\n")) {
    if (linha === "" || linha.startsWith(":")) continue;
    const separador = linha.indexOf(":");
    const campo = separador === -1 ? linha : linha.slice(0, separador);
    const valor = separador === -1 ? "" : linha.slice(separador + 1).replace(/^ /, "");
    if (campo === "event") tipo = valor;
    else if (campo === "data") linhasDeDados.push(valor);
  }
  if (linhasDeDados.length === 0) return null;
  const dados = lerDados(linhasDeDados.join("\n"));
  switch (tipo) {
    case "texto":
      if (typeof dados.texto !== "string") throw new ForaDoContrato();
      return { tipo: "texto", texto: dados.texto };
    case "estado":
      return { tipo: "estado" };
    case "fim":
      return { tipo: "fim" };
    case "erro":
      if (typeof dados.erro !== "string") throw new ForaDoContrato();
      return { tipo: "erro", mensagem: dados.erro };
    default:
      return null;
  }
}

function lerDados(json: string): Record<string, unknown> {
  let dados: unknown;
  try {
    dados = JSON.parse(json);
  } catch {
    throw new ForaDoContrato();
  }
  if (typeof dados !== "object" || dados === null) throw new ForaDoContrato();
  return dados as Record<string, unknown>;
}
