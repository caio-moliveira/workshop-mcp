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

const SEM_AVALIACOES = "Sem avaliações no período";

/** Os quatro cartões. O do catálogo não depende do período e aparece sempre; num período sem
 * avaliações, os outros três dizem só isso, sem valor nem variação. */
export function CartoesDeIndicadores({
  dados,
  periodo,
}: {
  dados: IndicadoresDeProdutos;
  periodo: Periodo;
}) {
  const avaliados = dados.produtos_avaliados.atual;
  return (
    <div className={estilos.grade}>
      {/* O catálogo não depende do período: sem variação (FE §6). */}
      <KpiCard
        rotulo="Produtos no catálogo"
        valor={formatarNumero(dados.catalogo)}
        legenda={`${contagem(avaliados, "avaliado", "avaliados")} no período`}
      />
      {dados.avaliacoes.atual === 0 ? (
        <>
          <KpiCard rotulo="Nota média" valor="—" legenda={SEM_AVALIACOES} />
          <KpiCard rotulo="Produtos mal avaliados" valor="—" legenda={SEM_AVALIACOES} />
          <KpiCard rotulo="Avaliações recebidas" valor="0" legenda={SEM_AVALIACOES} />
        </>
      ) : (
        <CartoesDoPeriodo dados={dados} periodo={periodo} />
      )}
    </div>
  );
}

function CartoesDoPeriodo({ dados, periodo }: { dados: IndicadoresDeProdutos; periodo: Periodo }) {
  const { nota_media: nota, produtos_mal_avaliados: malAvaliados, avaliacoes } = dados;
  return (
    <>
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
    </>
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
      {(dados) => <CartoesDeIndicadores dados={dados} periodo={periodo} />}
    </EstadosDoBloco>
  );
}
