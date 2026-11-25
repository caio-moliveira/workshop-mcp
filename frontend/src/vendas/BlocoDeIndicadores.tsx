import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { KpiCard } from "../componentes/KpiCard";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarMoeda, formatarNumero, formatarPercentual } from "../formatacao";
import estilos from "../painel/GradeDeIndicadores.module.css";
import type { Periodo } from "../painel/periodo";
import { variacaoDoIndicador } from "../painel/variacao";
import { VariacaoDoCartao } from "../painel/VariacaoDoCartao";
import { useBloco, type FonteDeDados } from "../useBloco";
import { eIndicadoresDeVendas, type IndicadoresDeVendas } from "./indicadores";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
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
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(pedidos.atual, pedidos.anterior, "relativa", "sobe")}
            periodo={periodo}
          />
        }
      />
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
        rotulo="Taxa de atraso"
        valor={taxa(atraso.atual)}
        legenda={`${atrasos} entre os pedidos entregues`}
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(
              atraso.atual,
              atraso.anterior,
              "pontos_percentuais",
              "desce",
            )}
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Taxa de aprovação"
        valor={taxa(aprovacao.atual)}
        legenda="Pedidos com pagamento aprovado"
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(
              aprovacao.atual,
              aprovacao.anterior,
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
