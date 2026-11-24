import type { ReactNode } from "react";

import estilos from "./PageHeading.module.css";

interface Propriedades {
  /** Microtexto superior: o setor ou o contexto. */
  contexto: string;
  titulo: string;
  subtitulo: string;
  /** Controles discretos, alinhados à direita (FE §5), como o PeriodFilter. */
  controles?: ReactNode;
}

/** Cabeçalho do conteúdo (FE §5). */
export function PageHeading({ contexto, titulo, subtitulo, controles }: Propriedades) {
  return (
    <header className={estilos.cabecalho}>
      <div className={estilos.textos}>
        <p className={estilos.contexto}>{contexto}</p>
        <h1 className={estilos.titulo}>{titulo}</h1>
        <p className={estilos.subtitulo}>{subtitulo}</p>
      </div>
      {controles && <div className={estilos.controles}>{controles}</div>}
    </header>
  );
}
