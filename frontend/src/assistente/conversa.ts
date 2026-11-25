/**
 * O estado da conversa com o assistente, sem React nem rede: cada pergunta enviada abre uma
 * resposta, e os eventos do fluxo vão preenchendo a resposta em andamento.
 *
 * Para estender (parada pelo usuário, aviso no fim, conversa reenviada): uma situação nova em
 * `RespostaDoAssistente` e o caso dela em `receber` ou numa função irmã de `enviar`.
 */
import type { EventoDaResposta } from "./fluxo";

export interface PerguntaDoUsuario {
  autor: "usuario";
  texto: string;
}

export interface RespostaDoAssistente {
  autor: "assistente";
  /** O texto recebido até agora; fica na tela mesmo quando a resposta termina em erro. */
  texto: string;
  situacao: "chegando" | "concluida" | "erro";
  /** O assistente está consultando os dados (evento `estado`) e ainda não voltou a escrever. */
  consultando: boolean;
  /** A mensagem genérica, quando a resposta terminou em erro. */
  erro?: string;
  /** O aviso do fim (teto de chamadas): a resposta concluiu, mas parou antes. */
  aviso?: string;
}

export type Fala = PerguntaDoUsuario | RespostaDoAssistente;

export interface Conversa {
  falas: readonly Fala[];
}

export const CONVERSA_VAZIA: Conversa = { falas: [] };

function respostaEmAndamento(conversa: Conversa): RespostaDoAssistente | null {
  const ultima = conversa.falas.at(-1);
  return ultima?.autor === "assistente" && ultima.situacao === "chegando" ? ultima : null;
}

/** Uma resposta ainda está chegando. */
export function respondendo(conversa: Conversa): boolean {
  return respostaEmAndamento(conversa) !== null;
}

/** Só uma pergunta por vez, e nunca em branco. */
export function podeEnviar(conversa: Conversa, pergunta: string): boolean {
  return pergunta.trim() !== "" && !respondendo(conversa);
}

/** A pergunta entra na conversa com a resposta dela ainda vazia. Sem envio possível, nada muda. */
export function enviar(conversa: Conversa, pergunta: string): Conversa {
  if (!podeEnviar(conversa, pergunta)) return conversa;
  return {
    falas: [
      ...conversa.falas,
      { autor: "usuario", texto: pergunta },
      { autor: "assistente", texto: "", situacao: "chegando", consultando: false },
    ],
  };
}

/** Aplica um evento do fluxo à resposta em andamento. Sem resposta em andamento, nada muda. */
export function receber(conversa: Conversa, evento: EventoDaResposta): Conversa {
  const atual = respostaEmAndamento(conversa);
  if (!atual) return conversa;
  let nova: RespostaDoAssistente;
  switch (evento.tipo) {
    case "texto":
      nova = { ...atual, texto: atual.texto + evento.texto, consultando: false };
      break;
    case "estado":
      nova = { ...atual, consultando: true };
      break;
    case "fim":
      nova = { ...atual, situacao: "concluida", consultando: false };
      if (evento.aviso) nova.aviso = evento.aviso;
      break;
    case "erro":
      nova = { ...atual, situacao: "erro", consultando: false, erro: evento.mensagem };
      break;
  }
  return { falas: [...conversa.falas.slice(0, -1), nova] };
}
