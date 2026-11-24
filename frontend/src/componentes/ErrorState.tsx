import estilos from "./ErrorState.module.css";
import { IconeAviso } from "./icones";

interface Propriedades {
  titulo: string;
  descricao: string;
  /** Rótulo da única ação, por exemplo "Tentar de novo" ou "Sair". */
  acao: string;
  aoAcionar: () => void;
  /**
   * `pagina` ocupa a tela, para quando nada mais pode ser mostrado. `bloco` fica no lugar de um
   * bloco do painel, sem derrubar os outros (FE §10).
   */
  variante?: "pagina" | "bloco";
}

/** Erro sóbrio, com ícone e uma ação clara (FE §10). */
export function ErrorState({ titulo, descricao, acao, aoAcionar, variante = "pagina" }: Propriedades) {
  const Titulo = variante === "pagina" ? "h1" : "h2";
  const erro = (
    <section
      className={variante === "pagina" ? estilos.erro : `${estilos.erro} ${estilos.bloco}`}
      role="alert"
    >
      <span className={estilos.icone}>
        <IconeAviso />
      </span>
      <Titulo className={estilos.titulo}>{titulo}</Titulo>
      <p className={estilos.descricao}>{descricao}</p>
      <button type="button" className={estilos.acao} onClick={aoAcionar}>
        {acao}
      </button>
    </section>
  );
  return variante === "pagina" ? <div className={estilos.pagina}>{erro}</div> : erro;
}
