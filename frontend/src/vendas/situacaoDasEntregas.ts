/** O contrato de `GET /vendas/situacao-das-entregas`: números crus e datas ISO. */

import { type DatasDoPeriodo, eDatasDoPeriodo, eObjeto } from "./contrato";
import { SITUACOES_DE_ENTREGA, type SituacaoDeEntrega } from "./pedidosRecentes";

export interface PedidosNaSituacao {
  situacao: SituacaoDeEntrega;
  pedidos: number;
}

export interface SituacaoDasEntregas {
  periodo: DatasDoPeriodo;
  /** Sempre as quatro situações, na ordem de `SITUACOES_DE_ENTREGA`, com zero onde não há pedido. */
  situacoes: PedidosNaSituacao[];
}

function eContagem(valor: unknown): valor is number {
  return Number.isInteger(valor) && (valor as number) >= 0;
}

export function eSituacaoDasEntregas(valor: unknown): valor is SituacaoDasEntregas {
  if (!eObjeto(valor)) return false;
  const { situacoes } = valor;
  return (
    eDatasDoPeriodo(valor.periodo) &&
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
