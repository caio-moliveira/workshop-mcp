import { Bar, BarChart, CartesianGrid, LabelList, Tooltip, XAxis, YAxis } from "recharts";

import { ChartPanel } from "../componentes/ChartPanel";
import { DicaDoGrafico } from "../componentes/DicaDoGrafico";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { CURSOR, EIXO, GRADE, SEM_ANIMACAO, type SerieDoGrafico } from "../componentes/graficos";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarNumero, formatarNumeroCompacto } from "../formatacao";
import type { Periodo } from "../painel/periodo";
import { useBloco, type FonteDeDados } from "../useBloco";
import {
  eNotasDasAvaliacoes,
  semAvaliacoes,
  type AvaliacoesNaNota,
  type NotasDasAvaliacoes,
} from "./notas";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

const TITULO = "Avaliações por nota";
const NOTA = "Notas 1 e 2 são reclamações.";
const AVALIACOES: SerieDoGrafico = { rotulo: "Avaliações", cor: "var(--serie-1)", forma: "barra" };

function rotuloDaNota(nota: number): string {
  return `Nota ${nota}`;
}

function Grafico({ dados }: { dados: NotasDasAvaliacoes }) {
  return (
    <ChartPanel titulo={TITULO} descricao={NOTA} series={[AVALIACOES]}>
      <BarChart
        responsive
        data={dados.notas}
        margin={{ top: 20, right: 0, bottom: 0, left: 0 }}
        style={{ width: "100%", height: "100%" }}
      >
        <CartesianGrid {...GRADE} />
        <XAxis {...EIXO} dataKey="nota" tickFormatter={rotuloDaNota} />
        <YAxis {...EIXO} tickFormatter={formatarNumeroCompacto} allowDecimals={false} width={48} />
        <Tooltip
          cursor={CURSOR}
          {...SEM_ANIMACAO}
          content={({ active, payload }) => {
            const item = payload?.[0]?.payload as AvaliacoesNaNota | undefined;
            if (!active || !item) return null;
            return (
              <DicaDoGrafico
                titulo={rotuloDaNota(item.nota)}
                linhas={[{ ...AVALIACOES, valor: formatarNumero(item.avaliacoes) }]}
              />
            );
          }}
        />
        <Bar
          {...SEM_ANIMACAO}
          dataKey="avaliacoes"
          name={AVALIACOES.rotulo}
          fill={AVALIACOES.cor}
          radius={[3, 3, 0, 0]}
          maxBarSize={56}
        >
          <LabelList
            dataKey="avaliacoes"
            position="top"
            formatter={(valor) => formatarNumero(Number(valor))}
            fill="var(--text-secondary)"
            fontSize={12}
          />
        </Bar>
      </BarChart>
    </ChartPanel>
  );
}

/** A distribuição das avaliações do período pelas notas de 1 a 5, com estados próprios (FE §6, §10). */
export function BlocoDeNotas({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/produtos/notas?periodo=${periodo}`,
    eNotasDasAvaliacoes,
  );

  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="as avaliações por nota"
      carregando={
        <AnuncioDeCarregamento texto="Carregando as avaliações por nota…">
          <LoadingSkeleton forma="grafico" />
        </AnuncioDeCarregamento>
      }
    >
      {(dados) =>
        semAvaliacoes(dados) ? (
          <EmptyState
            titulo="Nenhuma avaliação no período"
            descricao="Não há avaliações nestes dias. Escolha um período maior."
          />
        ) : (
          <Grafico dados={dados} />
        )
      }
    </EstadosDoBloco>
  );
}
