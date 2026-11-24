/** O contrato de `GET /vendas/pedidos-recentes`: números crus e datas ISO, sem dado de cliente. */

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
  periodo: { inicio: string; fim: string };
  /** Do mais recente para o mais antigo, no máximo 20. */
  pedidos: PedidoRecente[];
}

const DATA_ISO = /^\d{4}-\d{2}-\d{2}$/;
// Data, hora e fuso obrigatórios: sem fuso, o navegador leria o instante no fuso dele.
const INSTANTE_ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;
const UF = /^[A-Z]{2}$/;

function eObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

function eTexto(valor: unknown): valor is string {
  return typeof valor === "string" && valor !== "";
}

function eUmDe<T extends string>(opcoes: readonly T[], valor: unknown): valor is T {
  return typeof valor === "string" && (opcoes as readonly string[]).includes(valor);
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
    typeof valor.valor === "number" &&
    Number.isFinite(valor.valor) &&
    eUmDe(SITUACOES_DE_PAGAMENTO, valor.pagamento) &&
    (valor.entrega === null || eUmDe(SITUACOES_DE_ENTREGA, valor.entrega))
  );
}

export function ePedidosRecentes(valor: unknown): valor is PedidosRecentes {
  if (!eObjeto(valor) || !eObjeto(valor.periodo)) return false;
  const { inicio, fim } = valor.periodo;
  const { pedidos } = valor;
  return (
    typeof inicio === "string" &&
    DATA_ISO.test(inicio) &&
    typeof fim === "string" &&
    DATA_ISO.test(fim) &&
    Array.isArray(pedidos) &&
    pedidos.length <= LIMITE_DE_PEDIDOS_RECENTES &&
    pedidos.every(ePedidoRecente)
  );
}
