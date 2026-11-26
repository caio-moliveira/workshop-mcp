import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { KpiCard } from "../componentes/KpiCard";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarMoeda, formatarNota, formatarNumero, formatarPercentual } from "../formatacao";
import estilos from "../painel/GradeDeIndicadores.module.css";
import type { Periodo } from "../painel/periodo";
import { variacaoDoIndicador } from "../painel/variacao";
import { VariacaoDoCartao } from "../painel/VariacaoDoCartao";
import { useBloco, type FonteDeDados } from "../useBloco";
import { eIndicadoresDaDiretoria, type IndicadoresDaDiretoria } from "./indicadores";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

function percentualOuTraco(fracao: number | null): string {
  return fracao === null ? "—" : formatarPercentual(fracao);
}

function legendaDaRetencao({ retencao }: IndicadoresDaDiretoria): string {
  if (retencao.retidos === null || retencao.clientes_do_periodo_anterior === null) {
    return "Sem período anterior nos dados";
  }
  return `${formatarNumero(retencao.retidos)} de ${formatarNumero(retencao.clientes_do_periodo_anterior)} clientes do período anterior compraram de novo`;
}

/**
 * Os quatro cartões. Subir é bom nos quatro: a receita varia em percentual, as duas taxas em
 * pontos percentuais e a satisfação em pontos de nota. Em 24 meses nenhum tem variação, e a
 * retenção mostra "—", porque não há período anterior nos dados; em 12 meses a retenção tem valor
 * e não tem variação, porque a dela precisaria de dois períodos para trás.
 */
export function CartoesDeIndicadores({
  dados,
  periodo,
}: {
  dados: IndicadoresDaDiretoria;
  periodo: Periodo;
}) {
  const { receita, taxa_de_recompra: recompra, satisfacao, retencao } = dados;
  return (
    <div className={estilos.grade}>
      <KpiCard
        rotulo="Receita"
        valor={formatarMoeda(receita.atual)}
        legenda="Pagamentos aprovados, com frete"
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(receita.atual, receita.anterior, "relativa", "sobe")}
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Taxa de recompra"
        valor={percentualOuTraco(recompra.atual)}
        legenda={
          recompra.clientes === 0
            ? "Sem clientes no período"
            : `${formatarNumero(recompra.clientes_com_recompra)} de ${formatarNumero(recompra.clientes)} clientes compraram de novo`
        }
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(
              recompra.atual,
              recompra.anterior,
              "pontos_percentuais",
              "sobe",
            )}
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Satisfação"
        valor={satisfacao.atual === null ? "—" : formatarNota(satisfacao.atual)}
        legenda={
          satisfacao.avaliacoes === 0
            ? "Sem avaliações no período"
            : `Nota média de ${formatarNumero(satisfacao.avaliacoes)} avaliações`
        }
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(satisfacao.atual, satisfacao.anterior, "pontos", "sobe")}
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Retenção"
        valor={percentualOuTraco(retencao.atual)}
        legenda={legendaDaRetencao(dados)}
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(
              retencao.atual,
              retencao.anterior,
              "pontos_percentuais",
              "sobe",
            )}
            periodo={periodo}
          />
        }
      />
    </div>
  );
}

/** Os quatro indicadores do painel da Diretoria, com estados próprios (FE §6, §10). */
export function BlocoDeIndicadores({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/diretoria/indicadores?periodo=${periodo}`,
    eIndicadoresDaDiretoria,
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
