import { useId, type ReactNode } from "react";

import estilos from "./MolduraDeTabela.module.css";

interface Propriedades {
  titulo: string;
  descricao: string;
  /** Enquanto a tabela carrega. */
  ocupado?: boolean;
  children: ReactNode;
}

/** A moldura de um bloco de tabela dos painéis: título e descrição sobre a tabela (FE §6). */
export function MolduraDeTabela({ titulo, descricao, ocupado, children }: Propriedades) {
  const idDoTitulo = useId();
  return (
    <section className={estilos.moldura} aria-labelledby={idDoTitulo} aria-busy={ocupado}>
      <header className={estilos.cabecalho}>
        <h2 id={idDoTitulo} className={estilos.titulo}>
          {titulo}
        </h2>
        <p className={estilos.descricao}>{descricao}</p>
      </header>
      {children}
    </section>
  );
}
