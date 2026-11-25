/**
 * O estado da conversa com o assistente, sem React nem rede: cada pergunta enviada abre uma
 * resposta, e os eventos do fluxo vão preenchendo a resposta em andamento.
 *
 * Para estender: uma situação nova em `RespostaDoAssistente` e o caso dela em `receber` ou numa
 * função irmã de `enviar`.
 */
import type { EventoDaResposta } from "./fluxo";
import { cortarNoLimite, ITENS_DA_CONVERSA, passouDoLimite } from "./limites";
import type { ItemDaConversa } from "./rede";

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
}

export type PerguntaOuResposta = PerguntaDoUsuario | RespostaDoAssistente;

export interface Conversa {
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
  return { perguntasERespostas: [...conversa.perguntasERespostas.slice(0, -1), nova] };
}

/** O usuário parou a resposta em andamento: o texto recebido fica, e o envio é liberado. */
export function parar(conversa: Conversa): Conversa {
  const atual = respostaEmAndamento(conversa);
  if (!atual) return conversa;
  const nova: RespostaDoAssistente = { ...atual, situacao: "interrompida", consultando: false };
  return { perguntasERespostas: [...conversa.perguntasERespostas.slice(0, -1), nova] };
}

/**
 * A conversa anterior que vai com a pergunta seguinte: cada pergunta com a sua resposta, só quando
 * a resposta foi concluída. Uma resposta interrompida, com erro ou ainda chegando fica de fora, e a
 * pergunta dela também, para o modelo não receber uma pergunta sem resposta.
 *
 * Vai só o que a API aceita: os pares mais recentes que cabem no teto de itens, e cada texto
 * dentro do teto de caracteres, cortado com a marca quando passa.
 */
export function itensParaEnviar(conversa: Conversa): ItemDaConversa[] {
  const itens: ItemDaConversa[] = [];
  conversa.perguntasERespostas.forEach((item, indice) => {
    if (item.autor !== "assistente" || item.situacao !== "concluida") return;
    const pergunta = conversa.perguntasERespostas[indice - 1];
    if (pergunta?.autor !== "usuario") return;
    itens.push(
      { autor: "usuario", texto: cortarNoLimite(pergunta.texto) },
      { autor: "assistente", texto: cortarNoLimite(item.texto) },
    );
  });
  // Um número par de itens: nenhum par pergunta e resposta fica pela metade.
  const cabem = ITENS_DA_CONVERSA - (ITENS_DA_CONVERSA % 2);
  return itens.slice(Math.max(0, itens.length - cabem));
}
