/**
 * O estado da conversa com o assistente, sem React nem rede: cada pergunta enviada abre uma
 * resposta, e os eventos do fluxo vão preenchendo a resposta em andamento.
 *
 * A conversa fica gravada na API (ADR 0009): daqui só sai o identificador dela com a pergunta
 * seguinte, nunca as perguntas e respostas anteriores.
 *
 * Para estender: uma situação nova em `RespostaDoAssistente` e o caso dela em `receber` ou numa
 * função irmã de `enviar`.
 */
import type { EventoDaResposta } from "./fluxo";
import { passouDoLimite } from "./limites";
import type { CorpoDaPergunta } from "./rede";

export interface PerguntaDoUsuario {
  autor: "usuario";
  texto: string;
}

export interface RespostaDoAssistente {
  autor: "assistente";
  /** O texto recebido até agora; fica na tela mesmo quando a resposta termina em erro ou é parada. */
  texto: string;
  situacao: "chegando" | "concluida" | "erro" | "interrompida";
  /** O assistente está consultando os dados (evento `estado`) e ainda não voltou a escrever. */
  consultando: boolean;
  /** A mensagem genérica, quando a resposta terminou em erro. */
  erro?: string;
  /** O aviso do fim (teto de chamadas): a resposta concluiu, mas parou antes. */
  aviso?: string;
  /** O identificador da pergunta que a API deu, quando o fluxo chegou a começar. */
  idDaPergunta?: string;
}

export type PerguntaOuResposta = PerguntaDoUsuario | RespostaDoAssistente;

export interface Conversa {
  /** A conversa gravada na API, depois que a primeira resposta começou; antes, nenhuma. */
  id?: string;
  perguntasERespostas: readonly PerguntaOuResposta[];
}

export const CONVERSA_VAZIA: Conversa = { perguntasERespostas: [] };

function respostaEmAndamento(conversa: Conversa): RespostaDoAssistente | null {
  const ultima = conversa.perguntasERespostas.at(-1);
  return ultima?.autor === "assistente" && ultima.situacao === "chegando" ? ultima : null;
}

/** Uma resposta ainda está chegando. */
export function respondendo(conversa: Conversa): boolean {
  return respostaEmAndamento(conversa) !== null;
}

/** Só uma pergunta por vez, nunca em branco e dentro do teto de caracteres. */
export function podeEnviar(conversa: Conversa, pergunta: string): boolean {
  return pergunta.trim() !== "" && !passouDoLimite(pergunta) && !respondendo(conversa);
}

/** A pergunta entra na conversa com a resposta dela ainda vazia. Sem envio possível, nada muda. */
export function enviar(conversa: Conversa, pergunta: string): Conversa {
  if (!podeEnviar(conversa, pergunta)) return conversa;
  return {
    ...conversa,
    perguntasERespostas: [
      ...conversa.perguntasERespostas,
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
    case "conversa":
      return comResposta(
        { ...conversa, id: evento.idDaConversa },
        { ...atual, idDaPergunta: evento.idDaPergunta },
      );
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
  return comResposta(conversa, nova);
}

/** A conversa com a resposta em andamento trocada pela nova. */
function comResposta(conversa: Conversa, nova: RespostaDoAssistente): Conversa {
  return { ...conversa, perguntasERespostas: [...conversa.perguntasERespostas.slice(0, -1), nova] };
}

/** O usuário parou a resposta em andamento: o texto recebido fica, e o envio é liberado. */
export function parar(conversa: Conversa): Conversa {
  const atual = respostaEmAndamento(conversa);
  if (!atual) return conversa;
  return comResposta(conversa, { ...atual, situacao: "interrompida", consultando: false });
}

/**
 * O corpo da pergunta: o texto e, depois que a API gravou a conversa, o identificador dela. A API
 * lê do histórico o que entrega ao modelo; uma conversa reenviada daqui seria recusada.
 */
export function corpoDaPergunta(conversa: Conversa, pergunta: string): CorpoDaPergunta {
  return conversa.id ? { pergunta, id_da_conversa: conversa.id } : { pergunta };
}
