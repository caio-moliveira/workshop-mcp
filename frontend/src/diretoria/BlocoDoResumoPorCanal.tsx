import type { ReactNode } from "react";

import { CANAIS } from "../comercial/canais";
import { DataTable, type Coluna } from "../componentes/DataTable";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarMoeda, formatarNota, formatarNumero, formatarPercentual } from "../formatacao";
import { MolduraDeTabela } from "../painel/MolduraDeTabela";
import type { Periodo } from "../painel/periodo";
import { useBloco, type EstadoDoBloco, type FonteDeDados } from "../useBloco";
import estilos from "./BlocoDoResumoPorCanal.module.css";
import { eResumoPorCanal, semPedidos, type ResumoDoCanal, type ResumoPorCanal } from "./resumo";

/** A célula de uma taxa vazia: o traço à vista e o motivo para leitores de tela. */
function vazia(motivo: string): ReactNode {
  return (
    <>
      <span className={estilos.secundario} aria-hidden="true">
        —
      </span>
      <span className="visualmente-oculto">{motivo}</span>
    </>
  );
}

const COLUNAS: Coluna<ResumoDoCanal>[] = [
  { titulo: "Canal", celula: (c) => c.canal },
  { titulo: "Pedidos", alinhamento: "fim", celula: (c) => formatarNumero(c.pedidos) },
  { titulo: "Receita", alinhamento: "fim", celula: (c) => formatarMoeda(c.receita) },
  {
    titulo: "Taxa de atraso",
    alinhamento: "fim",
    celula: (c) =>
      c.taxa_de_atraso === null
        ? vazia("Nenhum pedido entregue no período")
        : formatarPercentual(c.taxa_de_atraso),
  },
  {
    titulo: "Satisfação",
    alinhamento: "fim",
    celula: (c) =>
      c.satisfacao === null ? vazia("Nenhuma avaliação no período") : formatarNota(c.satisfacao),
  },
  {
    titulo: "Taxa de recompra",
    alinhamento: "fim",
    celula: (c) =>
      c.taxa_de_recompra === null
        ? vazia("Nenhum cliente no período")
        : formatarPercentual(c.taxa_de_recompra),
  },
];

const MOLDURA = {
  titulo: "Resumo por canal do lojista",
  descricao:
    "Pedidos, receita, atraso, satisfação e recompra dos lojistas de cada canal, do canal que " +
    "mais atrasa para o que menos atrasa. O cliente conta no canal do lojista da primeira compra.",
};

/** A tabela dos cinco canais, na ordem em que a API os devolve: a da taxa de atraso. */
export function TabelaDoResumoPorCanal({ canais }: { canais: ResumoDoCanal[] }) {
  return (
    <DataTable
      rotulo="Resumo por canal do lojista no período"
      colunas={COLUNAS}
      linhas={canais}
      chave={(c) => c.canal}
    />
  );
}

interface Busca {
  estado: EstadoDoBloco<ResumoPorCanal>;
  tentarDeNovo: () => void;
}

/**
 * O resumo por canal do lojista, em largura total, com os estados de carregamento, vazio e erro
 * (FE §6, §10). A resposta traz sempre os cinco canais: o canal sem entrega ou sem avaliação fica
 * na linha com a célula vazia, e só o período sem nenhum pedido vira o estado vazio. No celular,
 * a tabela rola na horizontal dentro da moldura.
 */
export function BlocoDoResumoPorCanal({ estado, tentarDeNovo }: Busca) {
  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="o resumo por canal"
      carregando={
        <MolduraDeTabela {...MOLDURA} ocupado>
          <AnuncioDeCarregamento texto="Carregando o resumo por canal…">
            <LoadingSkeleton forma="tabela" linhas={CANAIS.length} />
          </AnuncioDeCarregamento>
        </MolduraDeTabela>
      }
    >
      {(dados) =>
        semPedidos(dados.canais) ? (
          <EmptyState
            titulo="Nenhum pedido no período"
            descricao="Nenhum lojista vendeu nestes dias. Escolha um período maior para comparar os canais."
          />
        ) : (
          <MolduraDeTabela {...MOLDURA}>
            <TabelaDoResumoPorCanal canais={dados.canais} />
          </MolduraDeTabela>
        )
      }
    </EstadosDoBloco>
  );
}

/** O bloco do resumo, buscando a rota com o período do painel. */
export function ResumoPorCanalDoLojista({
  fonte,
  periodo,
}: {
  fonte: FonteDeDados;
  periodo: Periodo;
}) {
  const busca = useBloco(fonte, `/diretoria/resumo?periodo=${periodo}`, eResumoPorCanal);
  return <BlocoDoResumoPorCanal {...busca} />;
}
