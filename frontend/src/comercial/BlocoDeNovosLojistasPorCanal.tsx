import { Bar, BarChart, CartesianGrid, LabelList, Tooltip, XAxis, YAxis } from "recharts";

import { ChartPanel } from "../componentes/ChartPanel";
import { DicaDoGrafico } from "../componentes/DicaDoGrafico";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { CURSOR, EIXO, SEM_ANIMACAO } from "../componentes/graficos";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarNumero, formatarNumeroCompacto } from "../formatacao";
import type { Periodo } from "../painel/periodo";
import { useBloco, type FonteDeDados } from "../useBloco";
import {
  canaisPorNovosLojistas,
  eDesempenhoDosCanais,
  type DesempenhoDoCanal,
} from "./desempenhoDosCanais";
import { linhasDaDica, NOVOS_LOJISTAS } from "./dicaDosCanais";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

const TITULO = "Novos lojistas por canal";
const NOTA =
  "Leads que fecharam no período, pelo canal de chegada. A conversão do canal está na dica.";

// Barras horizontais: a grade fina acompanha o eixo dos valores, que aqui é o horizontal.
const GRADE_VERTICAL = {
  horizontal: false,
  vertical: true,
  stroke: "var(--grade-do-grafico)",
  strokeWidth: 1,
} as const;

function Grafico({ canais }: { canais: DesempenhoDoCanal[] }) {
  return (
    <ChartPanel titulo={TITULO} descricao={NOTA} series={[NOVOS_LOJISTAS]}>
      <BarChart
        responsive
        layout="vertical"
        data={canais}
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
        <YAxis {...EIXO} type="category" dataKey="canal" width={128} />
        <Tooltip
          cursor={CURSOR}
          {...SEM_ANIMACAO}
          content={({ active, payload }) => {
            const item = payload?.[0]?.payload as DesempenhoDoCanal | undefined;
            if (!active || !item) return null;
            return <DicaDoGrafico titulo={item.canal} linhas={linhasDaDica(item)} />;
          }}
        />
        <Bar
          {...SEM_ANIMACAO}
          dataKey="novos_lojistas"
          name={NOVOS_LOJISTAS.rotulo}
          fill={NOVOS_LOJISTAS.cor}
          radius={[0, 3, 3, 0]}
          maxBarSize={28}
        >
          <LabelList
            dataKey="novos_lojistas"
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

/**
 * Os cinco canais em barras, do que trouxe mais novos lojistas para o que trouxe menos; num
 * período sem nenhum novo lojista, o estado vazio.
 */
export function NovosLojistasPorCanal({ canais }: { canais: DesempenhoDoCanal[] }) {
  return canais.some((item) => item.novos_lojistas > 0) ? (
    <Grafico canais={canaisPorNovosLojistas(canais)} />
  ) : (
    <EmptyState
      titulo="Nenhum novo lojista no período"
      descricao="Nenhum lead fechou nestes dias, em nenhum canal. Escolha um período maior."
    />
  );
}

/**
 * Os novos lojistas do período por canal, com a conversão de cada canal na dica e estados
 * próprios (FE §6, §10).
 */
export function BlocoDeNovosLojistasPorCanal({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/comercial/canais?periodo=${periodo}`,
    eDesempenhoDosCanais,
  );

  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="os novos lojistas por canal"
      carregando={
        <AnuncioDeCarregamento texto="Carregando os novos lojistas por canal…">
          <LoadingSkeleton forma="grafico" />
        </AnuncioDeCarregamento>
      }
    >
      {(dados) => <NovosLojistasPorCanal canais={dados.canais} />}
    </EstadosDoBloco>
  );
}
