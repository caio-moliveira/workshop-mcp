import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { KpiCard } from "../componentes/KpiCard";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { TrendBadge } from "../componentes/TrendBadge";
import {
  formatarMoeda,
  formatarNumero,
  formatarPercentual,
  formatarPontosPercentuais,
  formatarVariacaoRelativa,
} from "../formatacao";
import { ROTULO_DO_PERIODO, type Periodo } from "../painel/periodo";
import {
  sentidoDaVariacao,
  tomDaVariacao,
  variacaoEmPontos,
  variacaoRelativa,
  type Melhora,
} from "../painel/variacao";
import { useBloco, type FonteDeDados } from "../useBloco";
import estilos from "./BlocoDeIndicadores.module.css";
import { eIndicadoresDeVendas, type IndicadoresDeVendas } from "./indicadores";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

/** A variação de um indicador, ou nada quando não há período anterior com que comparar. */
function Variacao({
  variacao,
  formatar,
  melhora,
  periodo,
}: {
  variacao: number | null;
  formatar: (valor: number) => string;
  melhora: Melhora;
  periodo: Periodo;
}) {
  if (variacao === null) return null;
  return (
    <TrendBadge
      texto={formatar(variacao)}
      sentido={sentidoDaVariacao(variacao)}
      tom={tomDaVariacao(variacao, melhora)}
      comparacao={`em relação aos ${ROTULO_DO_PERIODO[periodo]} anteriores`}
    />
  );
}

function Indicadores({ dados, periodo }: { dados: IndicadoresDeVendas; periodo: Periodo }) {
  const { pedidos_realizados: pedidos, receita, taxa_de_atraso: atraso } = dados;
  const aprovacao = dados.taxa_de_aprovacao;
  const taxa = (valor: number | null) => (valor === null ? "—" : formatarPercentual(valor));
  const atrasos = atraso.atrasos === 1 ? "1 atraso" : `${formatarNumero(atraso.atrasos)} atrasos`;
  return (
    <div className={estilos.grade}>
      <KpiCard
        rotulo="Pedidos realizados"
        valor={formatarNumero(pedidos.atual)}
        legenda="Inclui pagamentos recusados"
        variacao={
          <Variacao
            variacao={variacaoRelativa(pedidos.atual, pedidos.anterior)}
            formatar={formatarVariacaoRelativa}
            melhora="sobe"
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Receita"
        valor={formatarMoeda(receita.atual)}
        legenda="Pagamentos aprovados, com frete"
        variacao={
          <Variacao
            variacao={variacaoRelativa(receita.atual, receita.anterior)}
            formatar={formatarVariacaoRelativa}
            melhora="sobe"
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Taxa de atraso"
        valor={taxa(atraso.atual)}
        legenda={`${atrasos} entre os pedidos entregues`}
        variacao={
          <Variacao
            variacao={variacaoEmPontos(atraso.atual, atraso.anterior)}
            formatar={formatarPontosPercentuais}
            melhora="desce"
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Taxa de aprovação"
        valor={taxa(aprovacao.atual)}
        legenda="Pedidos com pagamento aprovado"
        variacao={
          <Variacao
            variacao={variacaoEmPontos(aprovacao.atual, aprovacao.anterior)}
            formatar={formatarPontosPercentuais}
            melhora="sobe"
            periodo={periodo}
          />
        }
      />
    </div>
  );
}

/** Os quatro indicadores do painel de Vendas, com estados próprios (FE §6, §10). */
export function BlocoDeIndicadores({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/vendas/indicadores?periodo=${periodo}`,
    eIndicadoresDeVendas,
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
        dados.pedidos_realizados.atual === 0 ? (
          <EmptyState
            titulo="Nenhum pedido no período"
            descricao="Não há pedidos realizados nestes dias. Escolha um período maior para ver os indicadores."
          />
        ) : (
          <Indicadores dados={dados} periodo={periodo} />
        )
      }
    </EstadosDoBloco>
  );
}
