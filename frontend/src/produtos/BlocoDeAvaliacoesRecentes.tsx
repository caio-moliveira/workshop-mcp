import { useId, type ReactNode } from "react";

import { DataTable, type Coluna } from "../componentes/DataTable";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarData } from "../formatacao";
import type { Periodo } from "../painel/periodo";
import { useBloco, type FonteDeDados } from "../useBloco";
import {
  type AvaliacaoRecente,
  eAvaliacoesRecentes,
  LIMITE_DE_AVALIACOES_RECENTES,
} from "./avaliacoesRecentes";
import estilos from "./BlocoDeAvaliacoesRecentes.module.css";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

/** A avaliação e a posição dela na lista: a resposta não traz identificador da avaliação. */
type Linha = AvaliacaoRecente & { posicao: number };

const COLUNAS: Coluna<Linha>[] = [
  { titulo: "Produto", celula: (a) => a.nome_do_produto },
  { titulo: "Categoria", celula: (a) => <span className={estilos.secundario}>{a.categoria}</span> },
  {
    titulo: "Nota",
    alinhamento: "fim",
    celula: (a) => (
      <>
        <span className={estilos.nota}>{a.nota}</span>
        <span className="visualmente-oculto"> de 5</span>
      </>
    ),
  },
  { titulo: "Data", celula: (a) => formatarData(a.data) },
  {
    titulo: "Comentário",
    // Texto escrito por clientes (ADR 0010): vai como texto do React, que não interpreta HTML, e
    // nunca passa pelo Markdown.
    celula: (a) =>
      a.comentario === null ? (
        <>
          <span className={estilos.secundario} aria-hidden="true">
            —
          </span>
          <span className="visualmente-oculto">Sem comentário</span>
        </>
      ) : (
        <span className={estilos.comentario}>{a.comentario}</span>
      ),
  },
];

/** A tabela das avaliações, já carregadas. */
export function TabelaDeAvaliacoesRecentes({ avaliacoes }: { avaliacoes: AvaliacaoRecente[] }) {
  return (
    <DataTable
      rotulo="Avaliações recentes do período"
      colunas={COLUNAS}
      linhas={avaliacoes.map((avaliacao, posicao) => ({ ...avaliacao, posicao }))}
      chave={(a) => a.posicao}
    />
  );
}

/** A moldura do bloco: título e descrição sobre a tabela (FE §6). */
function Moldura({ children, ocupado }: { children: ReactNode; ocupado?: boolean }) {
  const idDoTitulo = useId();
  return (
    <section className={estilos.moldura} aria-labelledby={idDoTitulo} aria-busy={ocupado}>
      <header className={estilos.cabecalho}>
        <h2 id={idDoTitulo} className={estilos.titulo}>
          Avaliações recentes
        </h2>
        <p className={estilos.descricao}>
          As {LIMITE_DE_AVALIACOES_RECENTES} avaliações mais recentes do período, da mais nova
          para a mais antiga, com o comentário escrito pelo cliente.
        </p>
      </header>
      {children}
    </section>
  );
}

/** A tabela das avaliações mais recentes do período, com estados próprios (FE §6, §7, §10). */
export function BlocoDeAvaliacoesRecentes({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/produtos/avaliacoes?periodo=${periodo}`,
    eAvaliacoesRecentes,
  );

  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="as avaliações recentes"
      carregando={
        <Moldura ocupado>
          <AnuncioDeCarregamento texto="Carregando as avaliações recentes…">
            <LoadingSkeleton forma="tabela" linhas={8} />
          </AnuncioDeCarregamento>
        </Moldura>
      }
    >
      {(dados) =>
        dados.avaliacoes.length === 0 ? (
          <EmptyState
            titulo="Nenhuma avaliação no período"
            descricao="Não há avaliações nestes dias. Escolha um período maior para ver as avaliações recentes."
          />
        ) : (
          <Moldura>
            <TabelaDeAvaliacoesRecentes avaliacoes={dados.avaliacoes} />
          </Moldura>
        )
      }
    </EstadosDoBloco>
  );
}
