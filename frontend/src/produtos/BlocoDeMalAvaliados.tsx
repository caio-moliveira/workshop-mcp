import { DataTable, type Coluna } from "../componentes/DataTable";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarMoeda, formatarNota, formatarNumero } from "../formatacao";
import { MolduraDeTabela } from "../painel/MolduraDeTabela";
import type { Periodo } from "../painel/periodo";
import { useBloco, type FonteDeDados } from "../useBloco";
import estilos from "./BlocoDeMalAvaliados.module.css";
import { eMalAvaliados, type ProdutoMalAvaliado } from "./malAvaliados";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

const COLUNAS: Coluna<ProdutoMalAvaliado>[] = [
  { titulo: "Produto", celula: (p) => p.nome_do_produto },
  { titulo: "Categoria", celula: (p) => <span className={estilos.secundario}>{p.categoria}</span> },
  { titulo: "Preço", alinhamento: "fim", celula: (p) => formatarMoeda(p.preco) },
  {
    titulo: "Nota média",
    alinhamento: "fim",
    celula: (p) => <span className={estilos.nota}>{formatarNota(p.nota_media)}</span>,
  },
  { titulo: "Avaliações", alinhamento: "fim", celula: (p) => formatarNumero(p.avaliacoes) },
];

const MOLDURA = {
  titulo: "Produtos mal avaliados",
  descricao:
    "Nota média abaixo de 3,0 com pelo menos 3 avaliações no período, da pior nota para a " +
    "melhor.",
};

/** A tabela dos produtos mal avaliados do período, com estados próprios (FE §6, §10). */
export function BlocoDeMalAvaliados({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/produtos/mal-avaliados?periodo=${periodo}`,
    eMalAvaliados,
  );

  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="os produtos mal avaliados"
      carregando={
        <MolduraDeTabela {...MOLDURA} ocupado>
          <AnuncioDeCarregamento texto="Carregando os produtos mal avaliados…">
            <LoadingSkeleton forma="tabela" linhas={6} />
          </AnuncioDeCarregamento>
        </MolduraDeTabela>
      }
    >
      {(dados) =>
        dados.produtos.length === 0 ? (
          <EmptyState
            titulo="Nenhum produto mal avaliado no período"
            descricao="Nenhum produto teve nota média abaixo de 3,0 com pelo menos 3 avaliações nestes dias."
          />
        ) : (
          <MolduraDeTabela {...MOLDURA}>
            <DataTable
              rotulo="Produtos mal avaliados do período"
              colunas={COLUNAS}
              linhas={dados.produtos}
              chave={(p) => p.produto}
            />
          </MolduraDeTabela>
        )
      }
    </EstadosDoBloco>
  );
}
