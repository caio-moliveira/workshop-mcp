import { Bar, BarChart, CartesianGrid, LabelList, Tooltip, XAxis, YAxis } from "recharts";

import { ChartPanel } from "../componentes/ChartPanel";
import { DicaDoGrafico } from "../componentes/DicaDoGrafico";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import {
  CURSOR,
  EIXO,
  GRADE_VERTICAL,
  SEM_ANIMACAO,
  type SerieDoGrafico,
} from "../componentes/graficos";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarNota, formatarNumero, formatarPercentual } from "../formatacao";
import type { Periodo } from "../painel/periodo";
import { useBloco, type FonteDeDados } from "../useBloco";
import estilos from "./BlocoDosFatoresDeRecompra.module.css";
import {
  linhasDaDicaDeRecompra,
  linhasDaDicaDeSatisfacao,
  SATISFACAO,
  TAXA_DE_RECOMPRA,
  type LinhaDaDica,
} from "./dicaDosFatores";
import {
  eFatoresDeRecompra,
  semGrupos,
  type FatoresDeRecompra,
  type GrupoDeRecompra,
  type GrupoDeSatisfacao,
} from "./fatores";

interface Barra {
  grupo: string;
  /** O valor da barra; zero no grupo vazio, que a dica e o texto mostram como "—". */
  valor: number;
  rotulo: string;
  dica: LinhaDaDica[];
}

interface PropriedadesDoGrafico {
  titulo: string;
  descricao: string;
  serie: SerieDoGrafico;
  /** O que as barras são, para o texto dos leitores de tela. */
  porExtenso: string;
  barras: Barra[];
  /** O fim do eixo dos valores: 1 nas taxas, 5 na satisfação. */
  maximo: number;
  formatarEixo: (valor: number) => string;
}

/**
 * As barras de um bloco. O gráfico recebe o foco do teclado e as setas percorrem as barras (a
 * camada de acessibilidade do Recharts); o mesmo conteúdo vai em texto para os leitores de tela.
 */
function GraficoDoBloco({
  titulo,
  descricao,
  serie,
  porExtenso,
  barras,
  maximo,
  formatarEixo,
}: PropriedadesDoGrafico) {
  const texto = barras.map((barra) => `${barra.grupo}, ${barra.rotulo}`).join("; ");
  return (
    <ChartPanel titulo={titulo} descricao={descricao} series={[serie]}>
      <p className="visualmente-oculto">{`${porExtenso}: ${texto}.`}</p>
      <BarChart
        responsive
        accessibilityLayer
        layout="vertical"
        data={barras}
        margin={{ top: 4, right: 56, bottom: 0, left: 0 }}
        style={{ width: "100%", height: "100%" }}
      >
        <CartesianGrid {...GRADE_VERTICAL} />
        <XAxis {...EIXO} type="number" domain={[0, maximo]} tickFormatter={formatarEixo} />
        <YAxis {...EIXO} type="category" dataKey="grupo" width={104} />
        <Tooltip
          cursor={CURSOR}
          {...SEM_ANIMACAO}
          content={({ active, payload }) => {
            const barra = payload?.[0]?.payload as Barra | undefined;
            if (!active || !barra) return null;
            return <DicaDoGrafico titulo={barra.grupo} linhas={barra.dica} />;
          }}
        />
        <Bar
          {...SEM_ANIMACAO}
          dataKey="valor"
          name={serie.rotulo}
          fill={serie.cor}
          radius={[0, 3, 3, 0]}
          maxBarSize={24}
        >
          <LabelList dataKey="rotulo" position="right" fill="var(--text-secondary)" fontSize={12} />
        </Bar>
      </BarChart>
    </ChartPanel>
  );
}

function percentualOuTraco(fracao: number | null): string {
  return fracao === null ? "—" : formatarPercentual(fracao);
}

function barrasDeRecompra(grupos: GrupoDeRecompra[]): Barra[] {
  return grupos.map((item) => ({
    grupo: item.grupo,
    valor: item.taxa_de_recompra ?? 0,
    rotulo: percentualOuTraco(item.taxa_de_recompra),
    dica: linhasDaDicaDeRecompra(item),
  }));
}

function barrasDeSatisfacao(grupos: GrupoDeSatisfacao[]): Barra[] {
  return grupos.map((item) => ({
    grupo: item.grupo,
    valor: item.satisfacao ?? 0,
    rotulo: item.satisfacao === null ? "—" : formatarNota(item.satisfacao),
    dica: linhasDaDicaDeSatisfacao(item),
  }));
}

/** O eixo das taxas, em percentual sem casa ("20%"). */
function percentualDoEixo(fracao: number): string {
  return `${Math.round(fracao * 100)}%`;
}

/**
 * Os três blocos dos fatores de recompra: a taxa de recompra pela primeira entrega e pela primeira
 * nota do cliente, e a satisfação pela faixa de atraso. Num período sem cliente e sem avaliação, o
 * estado vazio.
 */
export function FatoresDeRecompraEmBlocos({ dados }: { dados: FatoresDeRecompra }) {
  if (semGrupos(dados)) {
    return (
      <EmptyState
        titulo="Nenhum cliente nem avaliação no período"
        descricao="Sem pedidos aprovados e sem avaliações nestes dias. Escolha um período maior."
      />
    );
  }
  return (
    <div className={estilos.blocos}>
      <GraficoDoBloco
        titulo="Recompra pela primeira entrega"
        descricao="Clientes do período pela entrega do primeiro pedido. Os em trânsito ou com prazo vencido ficam de fora."
        serie={TAXA_DE_RECOMPRA}
        porExtenso="Taxa de recompra dos clientes do período, pela entrega do primeiro pedido"
        barras={barrasDeRecompra(dados.primeira_entrega)}
        maximo={1}
        formatarEixo={percentualDoEixo}
      />
      <GraficoDoBloco
        titulo="Recompra pela primeira nota"
        descricao="Clientes do período pela nota que deram ao primeiro pedido. Quem não o avaliou fica de fora."
        serie={TAXA_DE_RECOMPRA}
        porExtenso="Taxa de recompra dos clientes do período, pela nota do primeiro pedido"
        barras={barrasDeRecompra(dados.primeira_nota)}
        maximo={1}
        formatarEixo={percentualDoEixo}
      />
      <GraficoDoBloco
        titulo="Satisfação pela faixa de atraso"
        descricao="Nota média das avaliações do período, pelo atraso da entrega do pedido avaliado."
        serie={SATISFACAO}
        porExtenso="Satisfação das avaliações do período, pela faixa de atraso da entrega"
        barras={barrasDeSatisfacao(dados.faixa_de_atraso)}
        maximo={5}
        formatarEixo={(nota) => formatarNumero(nota)}
      />
    </div>
  );
}

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

/** Os fatores de recompra do painel da Diretoria, com estados próprios (FE §6, §10). */
export function BlocoDosFatoresDeRecompra({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/diretoria/fatores-de-recompra?periodo=${periodo}`,
    eFatoresDeRecompra,
  );
  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="os fatores de recompra"
      carregando={
        <AnuncioDeCarregamento
          texto="Carregando os fatores de recompra…"
          className={estilos.blocos}
        >
          <LoadingSkeleton forma="grafico" />
          <LoadingSkeleton forma="grafico" />
          <LoadingSkeleton forma="grafico" />
        </AnuncioDeCarregamento>
      }
    >
      {(dados) => <FatoresDeRecompraEmBlocos dados={dados} />}
    </EstadosDoBloco>
  );
}
