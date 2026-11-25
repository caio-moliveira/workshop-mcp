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
import { eChamadaDoRastreio, type ChamadaDoRastreio, type EventoDaResposta } from "./fluxo";
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
  /** As chamadas terminadas que produziram a resposta, em ordem; vazio se nada foi consultado. */
  rastreio: readonly ChamadaDoRastreio[];
}

export type PerguntaOuResposta = PerguntaDoUsuario | RespostaDoAssistente;

export interface Conversa {
  /** A conversa gravada na API, depois que a primeira resposta começou; antes, nenhuma. */
  id?: string;
  perguntasERespostas: readonly PerguntaOuResposta[];
}

export const CONVERSA_VAZIA: Conversa = { perguntasERespostas: [] };

/** Começa outra conversa: a próxima pergunta vai sem identificador, e a API abre uma nova. */
export function comecarNova(): Conversa {
  return CONVERSA_VAZIA;
}

/** Como uma resposta terminada fica gravada: nunca "chegando". */
type SituacaoGravada = Exclude<RespostaDoAssistente["situacao"], "chegando">;

/** Um item da conversa como a rota `GET /conversas/{id}` o devolve: só os campos que ele tem. */
export type ItemLido =
  | { autor: "usuario"; texto: string }
  | {
      autor: "assistente";
      texto: string;
      situacao: SituacaoGravada;
      aviso?: string;
      erro?: string;
      id_da_pergunta?: string;
      rastreio: ChamadaDoRastreio[];
    };

/** A conversa lida do histórico, no contrato da rota. */
export interface ConversaLida {
  id: string;
  titulo: string;
  itens: ItemLido[];
}

/** A conversa como estava na tela quando foi gravada; a pergunta seguinte a continua. */
export function carregar(lida: ConversaLida): Conversa {
  return {
    id: lida.id,
    perguntasERespostas: lida.itens.map((item): PerguntaOuResposta => {
      if (item.autor === "usuario") return { autor: "usuario", texto: item.texto };
      const resposta: RespostaDoAssistente = {
        autor: "assistente",
        texto: item.texto,
        situacao: item.situacao,
        consultando: false,
        rastreio: item.rastreio,
      };
      if (item.aviso) resposta.aviso = item.aviso;
      if (item.erro) resposta.erro = item.erro;
      if (item.id_da_pergunta) resposta.idDaPergunta = item.id_da_pergunta;
      return resposta;
    }),
  };
}

const SITUACOES_GRAVADAS: readonly unknown[] = ["concluida", "erro", "interrompida"];

/** A resposta de `GET /conversas/{id}` está no contrato. Fora dele, não vira conversa na tela. */
export function eConversaLida(valor: unknown): valor is ConversaLida {
  if (typeof valor !== "object" || valor === null) return false;
  const { id, titulo, itens } = valor as Record<string, unknown>;
  return (
    typeof id === "string" &&
    typeof titulo === "string" &&
    Array.isArray(itens) &&
    itens.every(eItemLido)
  );
}

function eItemLido(valor: unknown): boolean {
  if (typeof valor !== "object" || valor === null) return false;
  const item = valor as Record<string, unknown>;
  if (typeof item.texto !== "string") return false;
  if (item.autor === "usuario") return true;
  return (
    item.autor === "assistente" &&
    SITUACOES_GRAVADAS.includes(item.situacao) &&
    opcionalDeTexto(item.aviso) &&
    opcionalDeTexto(item.erro) &&
    opcionalDeTexto(item.id_da_pergunta) &&
    Array.isArray(item.rastreio) &&
    item.rastreio.every(eChamadaDoRastreio)
  );
}

function opcionalDeTexto(valor: unknown): boolean {
  return valor === undefined || typeof valor === "string";
}

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
      { autor: "assistente", texto: "", situacao: "chegando", consultando: false, rastreio: [] },
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
    case "chamada": {
      const { ferramenta, desfecho, milissegundos } = evento;
      nova = { ...atual, rastreio: [...atual.rastreio, { ferramenta, desfecho, milissegundos }] };
      break;
    }
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
