/** O contrato de `GET /vendas/pedidos-recentes`: números crus e datas ISO, sem dado de cliente. */

import { type DatasDoPeriodo, eDatasDoPeriodo, eNumero, eObjeto, eUmDe } from "./contrato";

export const LIMITE_DE_PEDIDOS_RECENTES = 20;

export const SITUACOES_DE_PAGAMENTO = ["Aprovado", "Recusado"] as const;
export const SITUACOES_DE_ENTREGA = [
  "Em trânsito",
  "Prazo vencido",
  "Entregue no prazo",
  "Entregue com atraso",
] as const;

export type SituacaoDePagamento = (typeof SITUACOES_DE_PAGAMENTO)[number];
export type SituacaoDeEntrega = (typeof SITUACOES_DE_ENTREGA)[number];

export interface PedidoRecente {
  numero: number;
  /** Um instante ISO com fuso; a tela o mostra no horário de Brasília. */
  momento_compra: string;
  /** Do cliente, só a cidade e a UF. */
  cidade: string;
  uf: string;
  lojista: string;
  rota: string;
  valor: number;
  pagamento: SituacaoDePagamento;
  /** `null` quando não há entrega (pagamento recusado). */
  entrega: SituacaoDeEntrega | null;
}

export interface PedidosRecentes {
  periodo: DatasDoPeriodo;
  /** Do mais recente para o mais antigo, no máximo 20. */
  pedidos: PedidoRecente[];
}

// Data, hora e fuso obrigatórios: sem fuso, o navegador leria o instante no fuso dele.
const INSTANTE_ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;
const UF = /^[A-Z]{2}$/;

function eTexto(valor: unknown): valor is string {
  return typeof valor === "string" && valor !== "";
}

function ePedidoRecente(valor: unknown): valor is PedidoRecente {
  if (!eObjeto(valor)) return false;
  const { momento_compra: momento } = valor;
  return (
    Number.isInteger(valor.numero) &&
    typeof momento === "string" &&
    INSTANTE_ISO.test(momento) &&
    !Number.isNaN(Date.parse(momento)) &&
    eTexto(valor.cidade) &&
    typeof valor.uf === "string" &&
    UF.test(valor.uf) &&
    eTexto(valor.lojista) &&
    eTexto(valor.rota) &&
    eNumero(valor.valor) &&
    eUmDe(SITUACOES_DE_PAGAMENTO, valor.pagamento) &&
    (valor.entrega === null || eUmDe(SITUACOES_DE_ENTREGA, valor.entrega))
  );
}

export function ePedidosRecentes(valor: unknown): valor is PedidosRecentes {
  if (!eObjeto(valor)) return false;
  const { pedidos } = valor;
  return (
    eDatasDoPeriodo(valor.periodo) &&
    Array.isArray(pedidos) &&
    pedidos.length <= LIMITE_DE_PEDIDOS_RECENTES &&
    pedidos.every(ePedidoRecente)
  );
}
