import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { KpiCard } from "../componentes/KpiCard";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarNota, formatarNumero } from "../formatacao";
import estilos from "../painel/GradeDeIndicadores.module.css";
import type { Periodo } from "../painel/periodo";
import { variacaoDoIndicador } from "../painel/variacao";
import { VariacaoDoCartao } from "../painel/VariacaoDoCartao";
import { useBloco, type FonteDeDados } from "../useBloco";
import { eIndicadoresDeProdutos, type IndicadoresDeProdutos } from "./indicadores";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

function contagem(valor: number, singular: string, plural: string): string {
  return valor === 1 ? `1 ${singular}` : `${formatarNumero(valor)} ${plural}`;
}

function Indicadores({ dados, periodo }: { dados: IndicadoresDeProdutos; periodo: Periodo }) {
  const { nota_media: nota, produtos_mal_avaliados: malAvaliados, avaliacoes } = dados;
  const avaliados = dados.produtos_avaliados.atual;
  return (
    <div className={estilos.grade}>
      {/* O catálogo não depende do período: sem variação (FE §6). */}
      <KpiCard
        rotulo="Produtos no catálogo"
        valor={formatarNumero(dados.catalogo)}
        legenda={`${contagem(avaliados, "avaliado", "avaliados")} no período`}
      />
      <KpiCard
        rotulo="Nota média"
        valor={nota.atual === null ? "—" : formatarNota(nota.atual)}
        legenda="De 1 a 5, nas avaliações do período"
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(nota.atual, nota.anterior, "pontos", "sobe")}
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Produtos mal avaliados"
        valor={formatarNumero(malAvaliados.atual)}
        legenda="Nota média abaixo de 3,0, com 3 avaliações ou mais"
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(
              malAvaliados.atual,
              malAvaliados.anterior,
              "relativa",
              "desce",
            )}
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Avaliações recebidas"
        valor={formatarNumero(avaliacoes.atual)}
        legenda={`${contagem(dados.reclamacoes.atual, "reclamação", "reclamações")} (nota 1 ou 2)`}
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(avaliacoes.atual, avaliacoes.anterior, "relativa", "sobe")}
            periodo={periodo}
          />
        }
      />
    </div>
  );
}

/** Os quatro indicadores do painel de Produtos, com estados próprios (FE §6, §10). */
export function BlocoDeIndicadores({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/produtos/indicadores?periodo=${periodo}`,
    eIndicadoresDeProdutos,
  );

  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="os indicadores"
      carregando={
        <AnuncioDeCarregamento texto="Carregando os indicadores…" className={estilos.grade}>
          <LoadingSkeleton forma="cartao" />
          <LoadingSkeleton forma="cartao" />
          <LoadingSkeleton forma="cartao" />
          <LoadingSkeleton forma="cartao" />
        </AnuncioDeCarregamento>
      }
    >
      {(dados) =>
        dados.avaliacoes.atual === 0 ? (
          <EmptyState
            titulo="Nenhuma avaliação no período"
            descricao="Não há avaliações nestes dias. Escolha um período maior para ver os indicadores."
          />
        ) : (
          <Indicadores dados={dados} periodo={periodo} />
        )
      }
    </EstadosDoBloco>
  );
}
