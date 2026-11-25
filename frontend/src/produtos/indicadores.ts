/** O contrato de `GET /produtos/indicadores`: números crus e datas ISO. */

import {
  type Comparacao,
  type DatasDoPeriodo,
  eComparacao,
  eDatasDoPeriodo,
  eNumero,
  eObjeto,
} from "../painel/contrato";

export interface IndicadoresDeProdutos {
  periodo: DatasDoPeriodo;
  /** Todos os produtos do marketplace: não depende do período, e não tem anterior. */
  catalogo: number;
  produtos_avaliados: Comparacao<number>;
  /** De 1 a 5; `null` num período sem avaliações. */
  nota_media: Comparacao<number | null>;
  avaliacoes: Comparacao<number>;
  /** Avaliações com nota 1 ou 2. */
  reclamacoes: Comparacao<number>;
  /** Nota média abaixo de 3,0 com pelo menos 3 avaliações no período. */
  produtos_mal_avaliados: Comparacao<number>;
}

export function eIndicadoresDeProdutos(valor: unknown): valor is IndicadoresDeProdutos {
  return (
    eObjeto(valor) &&
    eDatasDoPeriodo(valor.periodo) &&
    eNumero(valor.catalogo) &&
    eComparacao(valor.produtos_avaliados, false) &&
    eComparacao(valor.nota_media, true) &&
    eComparacao(valor.avaliacoes, false) &&
    eComparacao(valor.reclamacoes, false) &&
    eComparacao(valor.produtos_mal_avaliados, false)
  );
}
