import estilos from "./ErrorState.module.css";
import { IconeAviso } from "./icones";

interface Propriedades {
  titulo: string;
  descricao: string;
  /** Rótulo da única ação, por exemplo "Tentar de novo" ou "Sair". */
  acao: string;
  aoAcionar: () => void;
}

/** Erro sóbrio, com ícone e uma ação clara (FE §10). */
export function ErrorState({ titulo, descricao, acao, aoAcionar }: Propriedades) {
  return (
    <div className={estilos.pagina}>
      <section className={estilos.erro} role="alert">
        <span className={estilos.icone}>
          <IconeAviso />
        </span>
        <h1 className={estilos.titulo}>{titulo}</h1>
        <p className={estilos.descricao}>{descricao}</p>
        <button type="button" className={estilos.acao} onClick={aoAcionar}>
          {acao}
        </button>
      </section>
    </div>
  );
}
