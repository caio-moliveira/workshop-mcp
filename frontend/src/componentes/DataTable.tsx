import type { ReactNode } from "react";

import estilos from "./DataTable.module.css";

export interface Coluna<T> {
  titulo: string;
  /** Textos à esquerda; valores numéricos à direita (FE §7). */
  alinhamento?: "inicio" | "fim";
  celula: (linha: T) => ReactNode;
}

interface Propriedades<T> {
  /** Nome da tabela para leitores de tela, também o da área de rolagem. */
  rotulo: string;
  colunas: Coluna<T>[];
  linhas: T[];
  chave: (linha: T) => string | number;
}

/**
 * Tabela densa do FE §7: cabeçalho de 12 px semibold, linhas de 54 px e divisórias tênues. No
 * celular, rola na horizontal dentro da própria moldura, com a primeira coluna fixa (FE §11).
 */
export function DataTable<T>({ rotulo, colunas, linhas, chave }: Propriedades<T>) {
  return (
    // A área de rolagem recebe foco para que o teclado também role a tabela.
    <div className={estilos.rolagem} role="region" aria-label={rotulo} tabIndex={0}>
      <table className={estilos.tabela}>
        <caption className="visualmente-oculto">{rotulo}</caption>
        <thead>
          <tr>
            {colunas.map((coluna) => (
              <th
                key={coluna.titulo}
                scope="col"
                className={coluna.alinhamento === "fim" ? estilos.fim : undefined}
              >
                {coluna.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((linha) => (
            <tr key={chave(linha)}>
              {colunas.map((coluna) => (
                <td
                  key={coluna.titulo}
                  className={coluna.alinhamento === "fim" ? estilos.fim : undefined}
                >
                  {coluna.celula(linha)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
