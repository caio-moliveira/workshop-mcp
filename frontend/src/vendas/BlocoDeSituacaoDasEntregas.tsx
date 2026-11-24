import { Bar, BarChart, CartesianGrid, LabelList, Tooltip, XAxis, YAxis } from "recharts";

import { ChartPanel } from "../componentes/ChartPanel";
import { DeniedState } from "../componentes/DeniedState";
import { DicaDoGrafico } from "../componentes/DicaDoGrafico";
import { EmptyState } from "../componentes/EmptyState";
import { ErrorState } from "../componentes/ErrorState";
import { CURSOR, EIXO, SEM_ANIMACAO, type SerieDoGrafico } from "../componentes/graficos";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarNumero, formatarNumeroCompacto } from "../formatacao";
import { useBloco, type FonteDeDados } from "../useBloco";
import type { Periodo } from "./periodo";
import {
  eSituacaoDasEntregas,
  semEntregas,
  type PedidosNaSituacao,
  type SituacaoDasEntregas,
} from "./situacaoDasEntregas";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

const TITULO = "Situação das entregas";
const NOTA = "Pedidos com pagamento recusado não têm entrega e ficam de fora.";
// A mesma série de pedidos da evolução, com a mesma cor: séries consistentes entre gráficos (FE §7).
const PEDIDOS: SerieDoGrafico = { rotulo: "Pedidos", cor: "var(--serie-1)", forma: "barra" };

// Barras horizontais: a grade fina acompanha o eixo dos valores, que aqui é o horizontal.
const GRADE_VERTICAL = {
  horizontal: false,
  vertical: true,
  stroke: "var(--grade-do-grafico)",
  strokeWidth: 1,
} as const;

function Grafico({ dados }: { dados: SituacaoDasEntregas }) {
  return (
    <ChartPanel titulo={TITULO} descricao={NOTA} series={[PEDIDOS]}>
      <BarChart
        responsive
        layout="vertical"
        data={dados.situacoes}
        margin={{ top: 4, right: 48, bottom: 0, left: 0 }}
        style={{ width: "100%", height: "100%" }}
      >
        <CartesianGrid {...GRADE_VERTICAL} />
        <XAxis
          {...EIXO}
          type="number"
          tickFormatter={formatarNumeroCompacto}
          allowDecimals={false}
        />
        <YAxis {...EIXO} type="category" dataKey="situacao" width={128} />
        <Tooltip
          cursor={CURSOR}
          {...SEM_ANIMACAO}
          content={({ active, payload }) => {
            const item = payload?.[0]?.payload as PedidosNaSituacao | undefined;
            if (!active || !item) return null;
            return (
              <DicaDoGrafico
                titulo={item.situacao}
                linhas={[{ ...PEDIDOS, valor: formatarNumero(item.pedidos) }]}
              />
            );
          }}
        />
        <Bar
          {...SEM_ANIMACAO}
          dataKey="pedidos"
          name={PEDIDOS.rotulo}
          fill={PEDIDOS.cor}
          radius={[0, 3, 3, 0]}
          maxBarSize={28}
        >
          <LabelList
            dataKey="pedidos"
            position="right"
            formatter={(valor) => formatarNumero(Number(valor))}
            fill="var(--text-secondary)"
            fontSize={12}
          />
        </Bar>
      </BarChart>
    </ChartPanel>
  );
}

/** A distribuição dos pedidos do período pelas situações de entrega, com estados próprios (FE §6, §10). */
export function BlocoDeSituacaoDasEntregas({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/vendas/situacao-das-entregas?periodo=${periodo}`,
    eSituacaoDasEntregas,
  );

  switch (estado.fase) {
    case "carregando":
      return (
        <div role="status" aria-live="polite">
          <span className="visualmente-oculto">Carregando a situação das entregas…</span>
          <LoadingSkeleton forma="grafico" />
        </div>
      );
    case "erro":
      return (
        <ErrorState
          variante="bloco"
          titulo="Não foi possível carregar a situação das entregas"
          descricao="O servidor não respondeu como esperado. Os outros blocos do painel não são afetados."
          acao="Tentar de novo"
          aoAcionar={tentarDeNovo}
        />
      );
    case "negado":
      return <DeniedState />;
    case "pronto":
      if (semEntregas(estado.dados)) {
        return (
          <EmptyState
            titulo="Nenhuma entrega no período"
            descricao="Não há pedidos com entrega nestes dias. Escolha um período maior."
          />
        );
      }
      return <Grafico dados={estado.dados} />;
  }
}
