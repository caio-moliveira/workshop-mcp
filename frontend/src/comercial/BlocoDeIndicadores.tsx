import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { KpiCard } from "../componentes/KpiCard";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarNumero, formatarPercentual } from "../formatacao";
import estilos from "../painel/GradeDeIndicadores.module.css";
import type { Periodo } from "../painel/periodo";
import { variacaoDoIndicador } from "../painel/variacao";
import { VariacaoDoCartao } from "../painel/VariacaoDoCartao";
import { useBloco, type FonteDeDados } from "../useBloco";
import { eIndicadoresDoComercial, type IndicadoresDoComercial } from "./indicadores";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

const SEM_LEADS = "Sem leads no período";

function legendaDosDiasAteFechar(dias: number | null): string {
  if (dias === null) return "Nenhum lead fechou no período";
  const inteiros = Math.round(dias);
  return inteiros === 1
    ? "1 dia até fechar, em média"
    : `${formatarNumero(inteiros)} dias até fechar, em média`;
}

/**
 * Os quatro cartões. Subir é bom em Leads, Novos lojistas e Conversão. O do principal canal mostra
 * um nome, não um número, e por isso não tem variação. Num período sem lead, a conversão e o
 * principal canal ficam sem valor; os quatro cartões continuam no lugar.
 */
export function CartoesDeIndicadores({
  dados,
  periodo,
}: {
  dados: IndicadoresDoComercial;
  periodo: Periodo;
}) {
  const { leads, novos_lojistas: novosLojistas, conversao } = dados;
  return (
    <div className={estilos.grade}>
      <KpiCard
        rotulo="Leads"
        valor={formatarNumero(leads.atual)}
        legenda={`${formatarNumero(dados.leads_em_negociacao)} em negociação`}
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(leads.atual, leads.anterior, "relativa", "sobe")}
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Novos lojistas"
        valor={formatarNumero(novosLojistas.atual)}
        legenda={legendaDosDiasAteFechar(dados.dias_ate_fechar)}
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(
              novosLojistas.atual,
              novosLojistas.anterior,
              "relativa",
              "sobe",
            )}
            periodo={periodo}
          />
        }
      />
      <KpiCard
        rotulo="Conversão"
        valor={conversao.atual === null ? "—" : formatarPercentual(conversao.atual)}
        legenda={conversao.atual === null ? SEM_LEADS : "Novos lojistas por leads do período"}
        variacao={
          <VariacaoDoCartao
            variacao={variacaoDoIndicador(
              conversao.atual,
              conversao.anterior,
              "pontos_percentuais",
              "sobe",
            )}
            periodo={periodo}
          />
        }
      />
      {/* Um nome, não um número: sem variação (FE §6). */}
      <KpiCard
        rotulo="Principal canal"
        valor={dados.principal_canal ?? "—"}
        legenda={
          dados.parcela_do_principal_canal === null
            ? SEM_LEADS
            : `${formatarPercentual(dados.parcela_do_principal_canal)} dos leads do período`
        }
      />
    </div>
  );
}

/** Os quatro indicadores do painel do Comercial, com estados próprios (FE §6, §10). */
export function BlocoDeIndicadores({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/comercial/indicadores?periodo=${periodo}`,
    eIndicadoresDoComercial,
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
