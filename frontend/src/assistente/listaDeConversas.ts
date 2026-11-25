/**
 * A lista das conversas do usuário, sem React nem rede: carregando, carregada (talvez vazia) ou
 * com erro, e a conversa apagada saindo dela.
 *
 * A ordem é a da API (`GET /conversas`): da última atividade mais recente para a mais antiga, só
 * as mais recentes. Nada daqui fica guardado no navegador entre cargas da página.
 */

/** Uma conversa como aparece na lista, sem as perguntas e respostas. */
export interface ResumoDaConversa {
  id: string;
  /** O começo da primeira pergunta. */
  titulo: string;
  /** Data e hora em ISO 8601, como a API manda. */
  ultimaAtividade: string;
}

export type ListaDeConversas =
  | { situacao: "carregando" }
  | { situacao: "carregada"; conversas: readonly ResumoDaConversa[] }
  | { situacao: "erro" };

export const LISTA_CARREGANDO: ListaDeConversas = { situacao: "carregando" };

/** A API não respondeu, ou respondeu fora do contrato. */
export function listaComErro(): ListaDeConversas {
  return { situacao: "erro" };
}

/** A resposta de `GET /conversas`, como a API a manda. */
export interface ListaLida {
  conversas: readonly { id: string; titulo: string; ultima_atividade: string }[];
}

/** A resposta de `GET /conversas` está no contrato. Fora dele, não vira lista na tela. */
export function eListaLida(valor: unknown): valor is ListaLida {
  if (typeof valor !== "object" || valor === null) return false;
  const { conversas } = valor as Record<string, unknown>;
  return Array.isArray(conversas) && conversas.every(eConversaNaLista);
}

function eConversaNaLista(valor: unknown): boolean {
  if (typeof valor !== "object" || valor === null) return false;
  const { id, titulo, ultima_atividade } = valor as Record<string, unknown>;
  return (
    typeof id === "string" && typeof titulo === "string" && typeof ultima_atividade === "string"
  );
}

/** A resposta de `GET /conversas`, já conferida, como lista carregada. */
export function listaRecebida(lida: ListaLida): ListaDeConversas {
  const conversas = lida.conversas.map(({ id, titulo, ultima_atividade }) => ({
    id,
    titulo,
    ultimaAtividade: ultima_atividade,
  }));
  return { situacao: "carregada", conversas };
}

/** Carregada e sem nenhuma conversa: o usuário ainda não perguntou nada, ou apagou todas. */
export function vazia(lista: ListaDeConversas): boolean {
  return lista.situacao === "carregada" && lista.conversas.length === 0;
}

/**
 * A lista depois de pedida de novo em segundo plano, com a lista já na tela (no modo expandido,
 * ao terminar uma resposta). Uma falha aí não apaga o que o usuário já via: a lista antiga ainda
 * serve para reabrir uma conversa, e a próxima atualização corrige a ordem.
 */
export function listaAtualizada(naTela: ListaDeConversas, nova: ListaDeConversas): ListaDeConversas {
  if (nova.situacao === "erro" && naTela.situacao === "carregada") return naTela;
  return nova;
}

/** A lista sem a conversa apagada. Só muda a lista carregada. */
export function semAConversa(lista: ListaDeConversas, id: string): ListaDeConversas {
  if (lista.situacao !== "carregada") return lista;
  return { ...lista, conversas: lista.conversas.filter((conversa) => conversa.id !== id) };
}
