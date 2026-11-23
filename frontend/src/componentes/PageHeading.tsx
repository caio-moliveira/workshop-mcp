import estilos from "./PageHeading.module.css";

interface Propriedades {
  /** Microtexto superior: o setor ou o contexto. */
  contexto: string;
  titulo: string;
  subtitulo: string;
}

/** Cabeçalho do conteúdo (FE §5). Os filtros chegam com os painéis. */
export function PageHeading({ contexto, titulo, subtitulo }: Propriedades) {
  return (
    <header className={estilos.cabecalho}>
      <p className={estilos.contexto}>{contexto}</p>
      <h1 className={estilos.titulo}>{titulo}</h1>
      <p className={estilos.subtitulo}>{subtitulo}</p>
    </header>
  );
}
