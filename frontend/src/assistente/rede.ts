import { ApiIndisponivel, TokenRecusado } from "../api";
import { lerEventos, type EventoDaResposta } from "./fluxo";

/** Uma fala anterior, como a rota `POST /assistente` a recebe. */
export interface ItemDaConversa {
  autor: "usuario" | "assistente";
  texto: string;
}

/** O corpo da rota `POST /assistente`. */
export interface CorpoDaPergunta {
  pergunta: string;
  conversa: ItemDaConversa[];
}

/**
 * Faz a pergunta com o token no cabeçalho Authorization e devolve os eventos da resposta. O
 * `EventSource` não serve: não faz POST nem manda cabeçalho. Um 401 vira `TokenRecusado`; qualquer
 * outra recusa antes do fluxo vira `ApiIndisponivel`.
 */
export async function* perguntarAoAssistente(
  enderecoDaApi: string,
  token: string,
  corpo: CorpoDaPergunta,
): AsyncGenerator<EventoDaResposta> {
  let resposta: Response;
  try {
    resposta = await fetch(`${enderecoDaApi}/assistente`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });
  } catch (erro) {
    throw new ApiIndisponivel(`sem resposta da API: ${String(erro)}`);
  }
  if (resposta.status === 401) throw new TokenRecusado();
  if (!resposta.ok || !resposta.body) {
    throw new ApiIndisponivel(`a API respondeu ${resposta.status}`);
  }
  yield* lerEventos(pedacosDe(resposta.body));
}

async function* pedacosDe(corpo: ReadableStream<Uint8Array>): AsyncGenerator<Uint8Array> {
  const leitor = corpo.getReader();
  try {
    for (;;) {
      const { value, done } = await leitor.read();
      if (done) return;
      yield value;
    }
  } finally {
    // Quem lê parou antes do fim do corpo (já veio o `fim`, ou deu erro): fecha a conexão.
    leitor.cancel().catch(() => undefined);
  }
}
