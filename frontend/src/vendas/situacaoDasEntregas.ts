/** O contrato de `GET /vendas/situacao-das-entregas`: números crus e datas ISO. */

import { SITUACOES_DE_ENTREGA, type SituacaoDeEntrega } from "./pedidosRecentes";

export interface PedidosNaSituacao {
  situacao: SituacaoDeEntrega;
  pedidos: number;
}

export interface SituacaoDasEntregas {
  periodo: { inicio: string; fim: string };
  /** Sempre as quatro situações, na ordem de `SITUACOES_DE_ENTREGA`, com zero onde não há pedido. */
  situacoes: PedidosNaSituacao[];
}

const DATA_ISO = /^\d{4}-\d{2}-\d{2}$/;

function eObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

function eContagem(valor: unknown): valor is number {
  return Number.isInteger(valor) && (valor as number) >= 0;
}

export function eSituacaoDasEntregas(valor: unknown): valor is SituacaoDasEntregas {
  if (!eObjeto(valor) || !eObjeto(valor.periodo)) return false;
  const { inicio, fim } = valor.periodo;
  const { situacoes } = valor;
  return (
    typeof inicio === "string" &&
    DATA_ISO.test(inicio) &&
    typeof fim === "string" &&
    DATA_ISO.test(fim) &&
    Array.isArray(situacoes) &&
    situacoes.length === SITUACOES_DE_ENTREGA.length &&
    situacoes.every(
      (item: unknown, i) =>
        eObjeto(item) && item.situacao === SITUACOES_DE_ENTREGA[i] && eContagem(item.pedidos),
    )
  );
}

/** Nenhum pedido do período em nenhuma situação: o bloco mostra o estado vazio. */
export function semEntregas(dados: SituacaoDasEntregas): boolean {
  return dados.situacoes.every((item) => item.pedidos === 0);
}
