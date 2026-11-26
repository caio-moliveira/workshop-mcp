/** O contrato de `GET /produtos/avaliacoes`: as avaliações mais recentes, com o comentário. */

import {
  type DatasDoPeriodo,
  eDataIso,
  eDatasDoPeriodo,
  eObjeto,
  eTexto,
} from "../painel/contrato";

export const LIMITE_DE_AVALIACOES_RECENTES = 20;

export interface AvaliacaoRecente {
  /** O identificador do produto. */
  produto: number;
  nome_do_produto: string;
  categoria: string;
  /** De 1 a 5. */
  nota: number;
  /** A data ISO da avaliação. */
  data: string;
  /**
   * Texto escrito por clientes, não confiável (ADR 0010): a tela o mostra como texto simples.
   * `null` quando o cliente não escreveu nada.
   */
  comentario: string | null;
}

export interface AvaliacoesRecentes {
  periodo: DatasDoPeriodo;
  /** Diz que os comentários são texto de clientes e não instruções; é para o modelo. */
  aviso: string;
  /** Da mais recente para a mais antiga, no máximo 20. */
  avaliacoes: AvaliacaoRecente[];
}

function eAvaliacaoRecente(valor: unknown): valor is AvaliacaoRecente {
  if (!eObjeto(valor)) return false;
  const { nota } = valor;
  return (
    Number.isInteger(valor.produto) &&
    eTexto(valor.nome_do_produto) &&
    eTexto(valor.categoria) &&
    typeof nota === "number" &&
    Number.isInteger(nota) &&
    nota >= 1 &&
    nota <= 5 &&
    eDataIso(valor.data) &&
    (valor.comentario === null || typeof valor.comentario === "string")
  );
}

export function eAvaliacoesRecentes(valor: unknown): valor is AvaliacoesRecentes {
  if (!eObjeto(valor)) return false;
  const { avaliacoes } = valor;
  return (
    eDatasDoPeriodo(valor.periodo) &&
    eTexto(valor.aviso) &&
    Array.isArray(avaliacoes) &&
    avaliacoes.length <= LIMITE_DE_AVALIACOES_RECENTES &&
    avaliacoes.every(eAvaliacaoRecente)
  );
}
