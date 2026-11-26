import { useId, type ReactNode } from "react";

import estilos from "./ChartPanel.module.css";
import type { SerieDoGrafico } from "./graficos";

interface Propriedades {
  titulo: string;
  /** Uma linha curta sob o título, quando o gráfico precisa de contexto. */
  descricao?: string;
  /** As séries, numa legenda discreta sob o título (FE §7). */
  series?: SerieDoGrafico[];
  /** O gráfico. Ocupa a largura do painel e a altura `--altura-do-grafico`. */
  children: ReactNode;
  /**
   * `livre` quando o conteúdo são vários gráficos pequenos, cada um com a própria altura, e a
   * área cresce com eles em vez de ter a altura fixa de um gráfico só. Se o painel for mais alto
   * que o conteúdo (esticado ao lado de outro bloco), a área ocupa a sobra, e o conteúdo a reparte.
   */
  altura?: "fixa" | "livre";
}

/** A marca de uma série: quadrado para barras, traço para linhas. */
export function MarcaDaSerie({ cor, forma }: Pick<SerieDoGrafico, "cor" | "forma">) {
  return (
    <span
      className={forma === "barra" ? estilos.marcaDeBarra : estilos.marcaDeLinha}
      style={{ background: cor }}
      aria-hidden="true"
    />
  );
}

/** Moldura de gráfico: fundo branco, borda fina, título, legenda discreta e o gráfico (FE §7, §12). */
export function ChartPanel({ titulo, descricao, series, children, altura = "fixa" }: Propriedades) {
  const idDoTitulo = useId();
  return (
    <section className={estilos.painel} aria-labelledby={idDoTitulo}>
      <header className={estilos.cabecalho}>
        <h2 id={idDoTitulo} className={estilos.titulo}>
          {titulo}
        </h2>
        {descricao && <p className={estilos.descricao}>{descricao}</p>}
        {series && series.length > 0 && (
          <ul className={estilos.legenda}>
            {series.map((serie) => (
              <li key={serie.rotulo} className={estilos.itemDaLegenda}>
                <MarcaDaSerie cor={serie.cor} forma={serie.forma} />
                {serie.rotulo}
              </li>
            ))}
          </ul>
        )}
      </header>
      <div className={altura === "fixa" ? estilos.grafico : estilos.graficos}>{children}</div>
    </section>
  );
}
