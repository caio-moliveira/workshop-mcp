import { Bar, CartesianGrid, ComposedChart, Line, Tooltip, XAxis, YAxis } from "recharts";

import { ChartPanel } from "../componentes/ChartPanel";
import { DeniedState } from "../componentes/DeniedState";
import { DicaDoGrafico } from "../componentes/DicaDoGrafico";
import { EmptyState } from "../componentes/EmptyState";
import { ErrorState } from "../componentes/ErrorState";
import { CURSOR, EIXO, GRADE, SEM_ANIMACAO, type SerieDoGrafico } from "../componentes/graficos";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import {
  formatarMoeda,
  formatarMoedaCompacta,
  formatarNumero,
  formatarNumeroCompacto,
} from "../formatacao";
import { useBloco, type FonteDeDados } from "../useBloco";
import {
  eEvolucaoDeVendas,
  rotuloDoEixo,
  rotuloDoIntervalo,
  semPedidos,
  type Agrupamento,
  type EvolucaoDeVendas,
  type PontoDaEvolucao,
} from "./evolucao";
import type { Periodo } from "./periodo";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

const TITULO = "Evolução de pedidos e receita";
const PEDIDOS: SerieDoGrafico = { rotulo: "Pedidos", cor: "var(--serie-1)", forma: "barra" };
const RECEITA: SerieDoGrafico = { rotulo: "Receita", cor: "var(--serie-2)", forma: "linha" };

const POR_AGRUPAMENTO: Record<Agrupamento, string> = {
  dia: "Por dia",
  semana: "Por semana, começando na segunda",
  mes: "Por mês",
};

function Grafico({ dados }: { dados: EvolucaoDeVendas }) {
  const { agrupamento, pontos } = dados;
  return (
    <ChartPanel titulo={TITULO} descricao={POR_AGRUPAMENTO[agrupamento]} series={[PEDIDOS, RECEITA]}>
      <ComposedChart
        responsive
        data={pontos}
        margin={{ top: 4, right: 0, bottom: 0, left: 0 }}
        style={{ width: "100%", height: "100%" }}
      >
        <CartesianGrid {...GRADE} />
        <XAxis
          {...EIXO}
          dataKey="inicio"
          tickFormatter={(inicio: string) => rotuloDoEixo(inicio, agrupamento)}
          minTickGap={12}
        />
        <YAxis
          {...EIXO}
          yAxisId="pedidos"
          tickFormatter={formatarNumeroCompacto}
          allowDecimals={false}
          width={48}
        />
        <YAxis
          {...EIXO}
          yAxisId="receita"
          orientation="right"
          tickFormatter={formatarMoedaCompacta}
          width={72}
        />
        <Tooltip
          cursor={CURSOR}
          {...SEM_ANIMACAO}
          content={({ active, payload }) => {
            const ponto = payload?.[0]?.payload as PontoDaEvolucao | undefined;
            if (!active || !ponto) return null;
            return (
              <DicaDoGrafico
                titulo={rotuloDoIntervalo(ponto.inicio, agrupamento)}
                linhas={[
                  { ...PEDIDOS, valor: formatarNumero(ponto.pedidos) },
                  { ...RECEITA, valor: formatarMoeda(ponto.receita) },
                ]}
              />
            );
          }}
        />
        <Bar
          {...SEM_ANIMACAO}
          yAxisId="pedidos"
          dataKey="pedidos"
          name={PEDIDOS.rotulo}
          fill={PEDIDOS.cor}
          radius={[3, 3, 0, 0]}
          maxBarSize={28}
        />
        <Line
          {...SEM_ANIMACAO}
          yAxisId="receita"
          dataKey="receita"
          name={RECEITA.rotulo}
          type="monotone"
          stroke={RECEITA.cor}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </ComposedChart>
    </ChartPanel>
  );
}

/** O gráfico de evolução de pedidos (barras) e receita (linha), com estados próprios (FE §6, §10). */
export function BlocoDeEvolucao({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/vendas/evolucao?periodo=${periodo}`,
    eEvolucaoDeVendas,
  );

  switch (estado.fase) {
    case "carregando":
      return (
        <div role="status" aria-live="polite">
          <span className="visualmente-oculto">Carregando a evolução de pedidos e receita…</span>
          <LoadingSkeleton forma="grafico" />
        </div>
      );
    case "erro":
      return (
        <ErrorState
          variante="bloco"
          titulo="Não foi possível carregar a evolução"
          descricao="O servidor não respondeu como esperado. Os outros blocos do painel não são afetados."
          acao="Tentar de novo"
          aoAcionar={tentarDeNovo}
        />
      );
    case "negado":
      return <DeniedState />;
    case "pronto":
      if (semPedidos(estado.dados)) {
        return (
          <EmptyState
            titulo="Nenhum pedido no período"
            descricao="Não há pedidos para desenhar a evolução nestes dias. Escolha um período maior."
          />
        );
      }
      return <Grafico dados={estado.dados} />;
  }
}
