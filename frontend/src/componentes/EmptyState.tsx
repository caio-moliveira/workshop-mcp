import estilos from "./EmptyState.module.css";
import { IconeEmBreve } from "./icones";

interface Propriedades {
  titulo: string;
  descricao: string;
}

/** Estado vazio: título pequeno, explicação curta e orientação (FE §10). */
export function EmptyState({ titulo, descricao }: Propriedades) {
  return (
    <section className={estilos.vazio} aria-labelledby="titulo-do-vazio">
      <span className={estilos.icone}>
        <IconeEmBreve />
      </span>
      <h2 id="titulo-do-vazio" className={estilos.titulo}>
        {titulo}
      </h2>
      <p className={estilos.descricao}>{descricao}</p>
    </section>
  );
}
