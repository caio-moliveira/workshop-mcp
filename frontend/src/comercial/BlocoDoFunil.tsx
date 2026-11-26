import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Rectangle,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartPanel } from "../componentes/ChartPanel";
import { DicaDoGrafico } from "../componentes/DicaDoGrafico";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { CURSOR, EIXO, GRADE, SEM_ANIMACAO, type SerieDoGrafico } from "../componentes/graficos";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarNumero, formatarNumeroCompacto } from "../formatacao";
import type { Periodo } from "../painel/periodo";
import { useBloco, type FonteDeDados } from "../useBloco";
import { PERDIDO, type Etapa } from "./etapas";
import { eFunilDoComercial, semLeads, type FunilDoComercial, type LeadsNaEtapa } from "./funil";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

const TITULO = "Leads por etapa do funil";
const NOTA = "Leads criados no período, na etapa atual de cada um.";
const NO_FUNIL: SerieDoGrafico = { rotulo: "Etapas do funil", cor: "var(--serie-1)", forma: "barra" };
// Perdido não é uma etapa seguinte a Fechado: fica por último, com outra cor (glossário).
const FORA_DO_FUNIL: SerieDoGrafico = { rotulo: PERDIDO, cor: "var(--serie-4)", forma: "barra" };

function serieDa(etapa: Etapa): SerieDoGrafico {
  return etapa === PERDIDO ? FORA_DO_FUNIL : NO_FUNIL;
}

/** As barras por extenso, para quem não vê o gráfico: a ordem do funil e Perdido à parte. */
function descricaoDasBarras(dados: FunilDoComercial): string {
  const porExtenso = ({ etapa, leads }: LeadsNaEtapa) => `${etapa}, ${formatarNumero(leads)}`;
  const noFunil = dados.etapas.filter((item) => item.etapa !== PERDIDO).map(porExtenso);
  const perdidos = dados.etapas.filter((item) => item.etapa === PERDIDO).map(porExtenso);
  return `Leads criados no período, pela etapa atual: ${noFunil.join("; ")}. À parte, ${perdidos.join("; ")}.`;
}

/**
 * As barras na ordem do funil, com Perdido por último e em outra cor. O gráfico recebe o foco do
 * teclado e as setas percorrem as barras (a camada de acessibilidade do Recharts); o mesmo
 * conteúdo vai em texto para os leitores de tela.
 */
export function GraficoDoFunil({ dados }: { dados: FunilDoComercial }) {
  return (
    <ChartPanel titulo={TITULO} descricao={NOTA} series={[NO_FUNIL, FORA_DO_FUNIL]}>
      <p className="visualmente-oculto">{descricaoDasBarras(dados)}</p>
      <BarChart
        responsive
        accessibilityLayer
        data={dados.etapas}
        margin={{ top: 20, right: 0, bottom: 0, left: 0 }}
        style={{ width: "100%", height: "100%" }}
      >
        <CartesianGrid {...GRADE} />
        <XAxis {...EIXO} dataKey="etapa" interval={0} />
        <YAxis {...EIXO} tickFormatter={formatarNumeroCompacto} allowDecimals={false} width={48} />
        <Tooltip
          cursor={CURSOR}
          {...SEM_ANIMACAO}
          content={({ active, payload }) => {
            const item = payload?.[0]?.payload as LeadsNaEtapa | undefined;
            if (!active || !item) return null;
            return (
              <DicaDoGrafico
                titulo={item.etapa}
                linhas={[
                  { ...serieDa(item.etapa), rotulo: "Leads", valor: formatarNumero(item.leads) },
                ]}
              />
            );
          }}
        />
        <Bar
          {...SEM_ANIMACAO}
          dataKey="leads"
          name="Leads"
          fill={NO_FUNIL.cor}
          radius={[3, 3, 0, 0]}
          maxBarSize={56}
          shape={(barra) => (
            <Rectangle {...barra} fill={serieDa((barra.payload as LeadsNaEtapa).etapa).cor} />
          )}
        >
          <LabelList
            dataKey="leads"
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

/** Os leads criados no período em cada etapa do funil, com estados próprios (FE §6, §10). */
export function BlocoDoFunil({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/comercial/funil?periodo=${periodo}`,
    eFunilDoComercial,
  );

  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="os leads por etapa do funil"
      carregando={
        <AnuncioDeCarregamento texto="Carregando os leads por etapa do funil…">
          <LoadingSkeleton forma="grafico" />
        </AnuncioDeCarregamento>
      }
    >
      {(dados) =>
        semLeads(dados) ? (
          <EmptyState
            titulo="Nenhum lead no período"
            descricao="Não há leads criados nestes dias. Escolha um período maior."
          />
        ) : (
          <GraficoDoFunil dados={dados} />
        )
      }
    </EstadosDoBloco>
  );
}
