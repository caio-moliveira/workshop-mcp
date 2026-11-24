import { useId } from "react";

import estilos from "./EmptyState.module.css";
import { IconeEmBreve } from "./icones";

interface Propriedades {
  titulo: string;
  descricao: string;
}

/** Estado vazio: título pequeno, explicação curta e orientação (FE §10). */
export function EmptyState({ titulo, descricao }: Propriedades) {
  const idDoTitulo = useId();
  return (
    <section className={estilos.vazio} aria-labelledby={idDoTitulo}>
      <span className={estilos.icone}>
        <IconeEmBreve />
      </span>
      <h2 id={idDoTitulo} className={estilos.titulo}>
        {titulo}
      </h2>
      <p className={estilos.descricao}>{descricao}</p>
    </section>
  );
}
