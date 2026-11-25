import { Bar, BarChart, CartesianGrid, LabelList, Tooltip, XAxis, YAxis } from "recharts";

import { ChartPanel } from "../componentes/ChartPanel";
import { DicaDoGrafico } from "../componentes/DicaDoGrafico";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { CURSOR, EIXO, SEM_ANIMACAO, type SerieDoGrafico } from "../componentes/graficos";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarNumero, formatarNumeroCompacto, formatarPercentual } from "../formatacao";
import type { Periodo } from "../painel/periodo";
import { useBloco, type FonteDeDados } from "../useBloco";
import {
  CATEGORIAS_NO_GRAFICO,
  categoriasComMaisReclamacoes,
  eCategoriasDeProdutos,
  type CategoriaDeProdutos,
} from "./categorias";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

const TITULO = "Categorias com mais reclamações";
const NOTA = `As ${CATEGORIAS_NO_GRAFICO} com mais avaliações de nota 1 ou 2 no período.`;
const RECLAMACOES: SerieDoGrafico = {
  rotulo: "Reclamações",
  cor: "var(--serie-1)",
  forma: "barra",
};
// A taxa só aparece na dica: a mesma marca, sem cor de série própria.
const TAXA: SerieDoGrafico = { rotulo: "Taxa de reclamação", cor: "transparent", forma: "barra" };

// Barras horizontais: a grade fina acompanha o eixo dos valores, que aqui é o horizontal.
const GRADE_VERTICAL = {
  horizontal: false,
  vertical: true,
  stroke: "var(--grade-do-grafico)",
  strokeWidth: 1,
} as const;

function Grafico({ categorias }: { categorias: CategoriaDeProdutos[] }) {
  return (
    <ChartPanel titulo={TITULO} descricao={NOTA} series={[RECLAMACOES]}>
      <BarChart
        responsive
        layout="vertical"
        data={categorias}
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
        <YAxis {...EIXO} type="category" dataKey="categoria" width={128} />
        <Tooltip
          cursor={CURSOR}
          {...SEM_ANIMACAO}
          content={({ active, payload }) => {
            const item = payload?.[0]?.payload as CategoriaDeProdutos | undefined;
            if (!active || !item) return null;
            return (
              <DicaDoGrafico
                titulo={item.categoria}
                linhas={[
                  { ...RECLAMACOES, valor: formatarNumero(item.reclamacoes) },
                  {
                    ...TAXA,
                    valor:
                      item.taxa_de_reclamacao === null
                        ? "—"
                        : formatarPercentual(item.taxa_de_reclamacao),
                  },
                ]}
              />
            );
          }}
        />
        <Bar
          {...SEM_ANIMACAO}
          dataKey="reclamacoes"
          name={RECLAMACOES.rotulo}
          fill={RECLAMACOES.cor}
          radius={[0, 3, 3, 0]}
          maxBarSize={28}
        >
          <LabelList
            dataKey="reclamacoes"
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
 * As categorias com mais reclamações no período, em número, com a taxa de reclamação na dica e
 * estados próprios (FE §6, §10).
 */
export function BlocoDeCategorias({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/produtos/categorias?periodo=${periodo}`,
    eCategoriasDeProdutos,
  );

  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="as categorias com mais reclamações"
      carregando={
        <AnuncioDeCarregamento texto="Carregando as categorias com mais reclamações…">
          <LoadingSkeleton forma="grafico" />
        </AnuncioDeCarregamento>
      }
    >
      {(dados) => {
        const categorias = categoriasComMaisReclamacoes(dados);
        return categorias.length === 0 ? (
          <EmptyState
            titulo="Nenhuma reclamação no período"
            descricao="Não há avaliações de nota 1 ou 2 nestes dias. Escolha um período maior."
          />
        ) : (
          <Grafico categorias={categorias} />
        );
      }}
    </EstadosDoBloco>
  );
}
