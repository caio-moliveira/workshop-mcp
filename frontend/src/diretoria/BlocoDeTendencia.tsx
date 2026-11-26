import { useId } from "react";
import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";

import { ChartPanel } from "../componentes/ChartPanel";
import { DicaDoGrafico } from "../componentes/DicaDoGrafico";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { CURSOR, EIXO, GRADE, SEM_ANIMACAO } from "../componentes/graficos";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import type { Periodo } from "../painel/periodo";
import { useBloco, type FonteDeDados } from "../useBloco";
import { rotuloDoEixo, rotuloDoPonto, type Agrupamento } from "../vendas/evolucao";
import estilos from "./BlocoDeTendencia.module.css";
import { INDICADORES, linhasDaDica, type IndicadorDaTendencia } from "./indicadoresDaTendencia";
import {
  eTendenciaDaDiretoria,
  semClientes,
  type PontoDaTendencia,
  type TendenciaDaDiretoria,
} from "./tendencia";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

const TITULO = "Tendência dos indicadores";

const POR_AGRUPAMENTO: Record<Agrupamento, string> = {
  dia: "Por dia",
  semana: "Por semana, começando na segunda",
  mes: "Por mês",
};

const POR_EXTENSO: Record<Agrupamento, string> = { dia: "dia", semana: "semana", mes: "mês" };

/** A série por extenso, para quem não vê o gráfico, na ordem dos pontos. */
function descricaoDaSerie(
  indicador: IndicadorDaTendencia,
  { agrupamento, pontos }: TendenciaDaDiretoria,
): string {
  const porExtenso = pontos.map((ponto) => {
    const valor = indicador.valor(ponto);
    const texto = valor === null ? indicador.vazio : indicador.formatar(valor);
    return `${rotuloDoPonto(ponto.inicio, agrupamento)}, ${texto}`;
  });
  return `${indicador.rotulo} por ${POR_EXTENSO[agrupamento]}: ${porExtenso.join("; ")}.`;
}

/**
 * Um gráfico pequeno, com escala própria. Ele recebe o foco do teclado e as setas percorrem os
 * pontos (a camada de acessibilidade do Recharts), com a dica do ponto; a mesma série vai em texto
 * para os leitores de tela. Um ponto vazio interrompe a linha, sem tirar o ponto da série.
 */
function GraficoPequeno({
  indicador,
  dados,
}: {
  indicador: IndicadorDaTendencia;
  dados: TendenciaDaDiretoria;
}) {
  const idDoRotulo = useId();
  const { agrupamento, pontos } = dados;
  const serie = pontos.map((ponto) => ({ ...ponto, valor: indicador.valor(ponto) }));
  return (
    <figure className={estilos.pequeno} aria-labelledby={idDoRotulo}>
      <h3 id={idDoRotulo} className={estilos.rotulo}>
        {indicador.rotulo}
      </h3>
      <p className="visualmente-oculto">{descricaoDaSerie(indicador, dados)}</p>
      <div className={estilos.grafico}>
        <LineChart
          responsive
          accessibilityLayer
          data={serie}
          margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
          style={{ width: "100%", height: "100%" }}
        >
          <CartesianGrid {...GRADE} />
          <XAxis
            {...EIXO}
            dataKey="inicio"
            tickFormatter={(inicio: string) => rotuloDoEixo(inicio, agrupamento)}
            minTickGap={16}
          />
          <YAxis
            {...EIXO}
            tickFormatter={indicador.formatarEixo}
            domain={["auto", "auto"]}
            width={56}
          />
          <Tooltip
            cursor={CURSOR}
            {...SEM_ANIMACAO}
            content={({ active, payload }) => {
              const ponto = payload?.[0]?.payload as PontoDaTendencia | undefined;
              if (!active || !ponto) return null;
              return (
                <DicaDoGrafico
                  titulo={rotuloDoPonto(ponto.inicio, agrupamento)}
                  linhas={linhasDaDica(indicador, ponto)}
                />
              );
            }}
          />
          <Line
            {...SEM_ANIMACAO}
            dataKey="valor"
            name={indicador.serie.rotulo}
            type="monotone"
            stroke={indicador.serie.cor}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            connectNulls={false}
          />
        </LineChart>
      </div>
    </figure>
  );
}

/**
 * Os quatro gráficos pequenos: receita, taxa de recompra, satisfação e taxa de atraso, cada um
 * com escala própria; num período sem nenhum cliente, o estado vazio.
 */
export function GraficosDaTendencia({ dados }: { dados: TendenciaDaDiretoria }) {
  if (semClientes(dados)) {
    return (
      <EmptyState
        titulo="Nenhum pedido aprovado no período"
        descricao="Não há pedidos para desenhar a tendência nestes dias. Escolha um período maior."
      />
    );
  }
  return (
    <ChartPanel titulo={TITULO} descricao={POR_AGRUPAMENTO[dados.agrupamento]} altura="livre">
      <div className={estilos.grade}>
        {INDICADORES.map((indicador) => (
          <GraficoPequeno key={indicador.rotulo} indicador={indicador} dados={dados} />
        ))}
      </div>
    </ChartPanel>
  );
}

/** A tendência dos quatro indicadores, o gráfico principal da Diretoria (FE §6, §10). */
export function BlocoDeTendencia({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/diretoria/tendencia?periodo=${periodo}`,
    eTendenciaDaDiretoria,
  );

  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="a tendência"
      carregando={
        <AnuncioDeCarregamento texto="Carregando a tendência dos indicadores…">
          <LoadingSkeleton forma="grafico" />
        </AnuncioDeCarregamento>
      }
    >
      {(dados) => <GraficosDaTendencia dados={dados} />}
    </EstadosDoBloco>
  );
}
