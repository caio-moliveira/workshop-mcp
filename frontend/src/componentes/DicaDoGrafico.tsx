import { MarcaDaSerie } from "./ChartPanel";
import estilos from "./DicaDoGrafico.module.css";
import type { LinhaDaDica } from "./graficos";

interface Propriedades {
  /** O ponto ou a categoria sob o ponteiro, por extenso. */
  titulo: string;
  /** Uma linha por série, com o valor já formatado. */
  linhas: LinhaDaDica[];
}

/** A dica de um gráfico: branca, raio 10 px, sombra suave e valores alinhados (FE §7). */
export function DicaDoGrafico({ titulo, linhas }: Propriedades) {
  return (
    <div className={estilos.dica}>
      <p className={estilos.titulo}>{titulo}</p>
      <dl className={estilos.linhas}>
        {linhas.map((linha) => (
          <div key={linha.rotulo} className={estilos.linha}>
            <dt className={estilos.rotulo}>
              <MarcaDaSerie cor={linha.cor} forma={linha.forma} />
              {linha.rotulo}
            </dt>
            <dd className={estilos.valor}>{linha.valor}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
