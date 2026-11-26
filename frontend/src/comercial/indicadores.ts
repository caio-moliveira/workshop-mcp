/** O contrato de `GET /comercial/indicadores`: números crus e datas ISO. */

import {
  type Comparacao,
  type DatasDoPeriodo,
  eComparacao,
  eDatasDoPeriodo,
  eNumero,
  eNumeroOuNulo,
  eObjeto,
  eUmDe,
} from "../painel/contrato";
import { CANAIS, type Canal } from "./canais";

export interface IndicadoresDoComercial {
  periodo: DatasDoPeriodo;
  /** Leads criados no período. */
  leads: Comparacao<number>;
  /** Entre os leads criados no período, os que ainda não fecharam nem foram perdidos. */
  leads_em_negociacao: number;
  /** Leads que fecharam no período, contados pela data de fechamento. */
  novos_lojistas: Comparacao<number>;
  /** Média de dias da criação ao fechamento; `null` num período sem novo lojista. */
  dias_ate_fechar: number | null;
  /** Novos lojistas ÷ leads do período, de 0 a 1; `null` num período sem lead. */
  conversao: Comparacao<number | null>;
  /** O canal que trouxe mais leads no período; `null` num período sem lead. */
  principal_canal: Canal | null;
  /** A parte do principal canal nos leads do período, de 0 a 1; `null` junto com o canal. */
  parcela_do_principal_canal: number | null;
}

/** O nome do canal e a parcela dele vêm juntos, ou os dois vazios. */
function ePrincipalCanal(canal: unknown, parcela: unknown): boolean {
  if (canal === null) return parcela === null;
  return eUmDe(CANAIS, canal) && eNumero(parcela);
}

export function eIndicadoresDoComercial(valor: unknown): valor is IndicadoresDoComercial {
  return (
    eObjeto(valor) &&
    eDatasDoPeriodo(valor.periodo) &&
    eComparacao(valor.leads, false) &&
    eNumero(valor.leads_em_negociacao) &&
    eComparacao(valor.novos_lojistas, false) &&
    eNumeroOuNulo(valor.dias_ate_fechar) &&
    eComparacao(valor.conversao, true) &&
    ePrincipalCanal(valor.principal_canal, valor.parcela_do_principal_canal)
  );
}
