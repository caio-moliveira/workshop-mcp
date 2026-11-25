import { ApiIndisponivel, TokenRecusado } from "../api";
import { lerEventos, type EventoDaResposta } from "./fluxo";

/** A pergunta nem chegou a virar fluxo: rede fora, token recusado ou recusa da rota. */
export const SEM_RESPOSTA = "Não foi possível obter a resposta agora. Tente de novo.";

/**
 * O aviso de reserva para o 503, só quando o corpo não traz o texto: quem escreve o aviso é a API,
 * no campo `erro` da resposta.
 */
export const ASSISTENTE_INDISPONIVEL = "O assistente está indisponível no momento.";

/** A rota respondeu 503: sem modelo configurado ou sem a chave do provedor. */
export class AssistenteIndisponivel extends Error {
  /** O aviso ao usuário, como a API o devolveu. */
  readonly aviso: string;

  constructor(aviso: string) {
    super("o assistente está indisponível");
    this.name = "AssistenteIndisponivel";
    this.aviso = aviso;
  }
}

/**
 * A conversa continuada não existe mais: foi apagada, quase sempre em outra aba. A API não diz
 * qual dos dois (inexistente ou de outro usuário), e daqui só pode ser a apagada.
 */
export const CONVERSA_APAGADA =
  "Esta conversa foi apagada e não pode ser continuada. Comece uma nova conversa.";

/** A rota respondeu 404 à pergunta que continuava uma conversa. */
export class ConversaApagada extends Error {
  constructor() {
    super("a conversa não existe mais");
    this.name = "ConversaApagada";
  }
}

/** O texto que fica no lugar da resposta quando a pergunta falha antes do fluxo. */
export function mensagemDaFalha(erro: unknown): string {
  if (erro instanceof AssistenteIndisponivel) return erro.aviso;
  if (erro instanceof ConversaApagada) return CONVERSA_APAGADA;
  return SEM_RESPOSTA;
}

/** O texto do campo `erro` do corpo JSON da recusa, ou o de reserva se ele não vier. */
async function avisoDaRecusa(resposta: Response, reserva: string): Promise<string> {
  try {
    const corpo: unknown = await resposta.json();
    if (typeof corpo === "object" && corpo !== null) {
      const { erro } = corpo as Record<string, unknown>;
      if (typeof erro === "string" && erro.trim() !== "") return erro;
    }
  } catch {
    // Corpo vazio ou fora do JSON: fica a reserva.
  }
  return reserva;
}

/**
 * O corpo da rota `POST /assistente`: a pergunta e, para continuar uma conversa gravada, o
 * identificador dela. Sem ele, a API abre uma conversa nova.
 */
export interface CorpoDaPergunta {
  pergunta: string;
  id_da_conversa?: string;
}

/**
 * Faz a pergunta com o token no cabeçalho Authorization e, aceita a pergunta, devolve os eventos
 * da resposta. O `EventSource` não serve: não faz POST nem manda cabeçalho. As recusas vêm antes do
 * fluxo, na promessa: um 401 vira `TokenRecusado`, um 404 vira `ConversaApagada`, um 503 vira
 * `AssistenteIndisponivel`; qualquer outra recusa vira `ApiIndisponivel`.
 * Abortar o `sinal` fecha a conexão, e a API cancela a resposta.
 */
export async function perguntarAoAssistente(
  enderecoDaApi: string,
  token: string,
  corpo: CorpoDaPergunta,
  sinal?: AbortSignal,
): Promise<AsyncGenerator<EventoDaResposta>> {
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
  if (resposta.status === 404) throw new ConversaApagada();
  if (resposta.status === 503) {
    throw new AssistenteIndisponivel(await avisoDaRecusa(resposta, ASSISTENTE_INDISPONIVEL));
  }
  if (!resposta.ok || !resposta.body) {
    throw new ApiIndisponivel(`a API respondeu ${resposta.status}`);
  }
  return lerEventos(pedacosDe(resposta.body));
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
