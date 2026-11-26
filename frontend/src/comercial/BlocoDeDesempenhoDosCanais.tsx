import { DataTable, type Coluna } from "../componentes/DataTable";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarNumero, formatarPercentual } from "../formatacao";
import { MolduraDeTabela } from "../painel/MolduraDeTabela";
import estilos from "./BlocoDeDesempenhoDosCanais.module.css";
import { CANAIS } from "./canais";
import { semMovimento, type BuscaDosCanais, type DesempenhoDoCanal } from "./desempenhoDosCanais";

const COLUNAS: Coluna<DesempenhoDoCanal>[] = [
  { titulo: "Canal", celula: (c) => c.canal },
  { titulo: "Leads", alinhamento: "fim", celula: (c) => formatarNumero(c.leads) },
  { titulo: "Novos lojistas", alinhamento: "fim", celula: (c) => formatarNumero(c.novos_lojistas) },
  {
    titulo: "Conversão",
    alinhamento: "fim",
    celula: (c) =>
      c.conversao === null ? (
        <>
          <span className={estilos.secundario} aria-hidden="true">
            —
          </span>
          <span className="visualmente-oculto">Sem leads no período</span>
        </>
      ) : (
        formatarPercentual(c.conversao)
      ),
  },
  {
    titulo: "Dias até fechar",
    alinhamento: "fim",
    celula: (c) =>
      c.dias_ate_fechar === null ? (
        <>
          <span className={estilos.secundario} aria-hidden="true">
            —
          </span>
          <span className="visualmente-oculto">Nenhum lead fechou no período</span>
        </>
      ) : (
        formatarNumero(Math.round(c.dias_ate_fechar))
      ),
  },
];

const MOLDURA = {
  titulo: "Desempenho dos canais",
  descricao:
    "Leads criados e novos lojistas do período em cada canal, da maior conversão para a menor. " +
    "A conversão são os novos lojistas por leads do período; com poucos leads, ela muda muito.",
};

/** A tabela dos canais, na ordem em que a API os devolve: a da conversão, com os vazios no fim. */
export function TabelaDeDesempenhoDosCanais({ canais }: { canais: DesempenhoDoCanal[] }) {
  return (
    <DataTable
      rotulo="Desempenho dos canais no período"
      colunas={COLUNAS}
      linhas={canais}
      chave={(c) => c.canal}
    />
  );
}

/**
 * A tabela de desempenho dos canais do período, com os estados da busca que o painel faz e divide
 * com o gráfico de novos lojistas (FE §6, §10). A resposta traz sempre os cinco canais: o canal
 * sem lead ou sem fechamento fica na linha com a célula vazia, e só o período sem nenhum lead e
 * sem nenhum novo lojista, em nenhum canal, vira o estado vazio.
 */
export function BlocoDeDesempenhoDosCanais({ estado, tentarDeNovo }: BuscaDosCanais) {
  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="o desempenho dos canais"
      carregando={
        <MolduraDeTabela {...MOLDURA} ocupado>
          <AnuncioDeCarregamento texto="Carregando o desempenho dos canais…">
            <LoadingSkeleton forma="tabela" linhas={CANAIS.length} />
          </AnuncioDeCarregamento>
        </MolduraDeTabela>
      }
    >
      {(dados) =>
        semMovimento(dados.canais) ? (
          <EmptyState
            titulo="Nenhum lead nem novo lojista no período"
            descricao="Nenhum canal trouxe lead ou fechou negócio nestes dias. Escolha um período maior para comparar os canais."
          />
        ) : (
          <MolduraDeTabela {...MOLDURA}>
            <TabelaDeDesempenhoDosCanais canais={dados.canais} />
          </MolduraDeTabela>
        )
      }
    </EstadosDoBloco>
  );
}
