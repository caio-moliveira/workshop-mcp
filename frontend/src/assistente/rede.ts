import { ApiIndisponivel, TokenRecusado } from "../api";
import { lerEventos, type EventoDaResposta } from "./fluxo";

/** A pergunta nem chegou a virar fluxo: rede fora, token recusado ou recusa da rota. */
export const SEM_RESPOSTA = "Não foi possível obter a resposta agora. Tente de novo.";

/** O mesmo texto de `ASSISTENTE_INDISPONIVEL` em `backend/acesso/mensagens.py`. */
export const ASSISTENTE_INDISPONIVEL =
  "O assistente está indisponível no momento. Tente de novo mais tarde.";

/** A rota respondeu 503: sem modelo configurado ou sem a chave do provedor. */
export class AssistenteIndisponivel extends Error {
  constructor() {
    super("o assistente está indisponível");
    this.name = "AssistenteIndisponivel";
  }
}

/** O texto que fica no lugar da resposta quando a pergunta falha antes do fluxo. */
export function mensagemDaFalha(erro: unknown): string {
  return erro instanceof AssistenteIndisponivel ? ASSISTENTE_INDISPONIVEL : SEM_RESPOSTA;
}

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
 * `EventSource` não serve: não faz POST nem manda cabeçalho. Um 401 vira `TokenRecusado`, um 503
 * vira `AssistenteIndisponivel`; qualquer outra recusa antes do fluxo vira `ApiIndisponivel`.
 * Abortar o `sinal` fecha a conexão, e a API cancela a resposta.
 */
export async function* perguntarAoAssistente(
  enderecoDaApi: string,
  token: string,
  corpo: CorpoDaPergunta,
  sinal?: AbortSignal,
): AsyncGenerator<EventoDaResposta> {
  let resposta: Response;
  try {
    resposta = await fetch(`${enderecoDaApi}/assistente`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
      signal: sinal,
    });
  } catch (erro) {
    throw new ApiIndisponivel(`sem resposta da API: ${String(erro)}`);
  }
  if (resposta.status === 401) throw new TokenRecusado();
  if (resposta.status === 503) throw new AssistenteIndisponivel();
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
