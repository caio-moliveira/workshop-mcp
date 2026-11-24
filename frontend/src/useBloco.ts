import { useEffect, useState } from "react";

import { AcessoNegado, TokenRecusado } from "./api";

/** Quem busca os dados de um bloco: a Sessao, que põe o token e cuida do 401. */
export interface FonteDeDados {
  consultar<T>(caminho: string, validar: (valor: unknown) => valor is T): Promise<T>;
}

type Resultado<T> = { fase: "pronto"; dados: T } | { fase: "erro" } | { fase: "negado" };

/** Cada bloco do painel carrega, falha, fica vazio ou é negado por conta própria (FE §10). */
export type EstadoDoBloco<T> = { fase: "carregando" } | Resultado<T>;

/**
 * Busca a rota de um bloco e acompanha o estado dela. Mudar o caminho (outro período) ou tentar de
 * novo volta o bloco a "carregando" e busca de novo. Um 401 não vira estado do bloco: a sessão já
 * está levando o usuário ao login.
 */
export function useBloco<T>(
  fonte: FonteDeDados,
  caminho: string,
  validar: (valor: unknown) => valor is T,
): { estado: EstadoDoBloco<T>; tentarDeNovo: () => void } {
  const [tentativa, setTentativa] = useState(0);
  const chave = `${tentativa} ${caminho}`;
  const [ultimo, setUltimo] = useState<{ chave: string; resultado: Resultado<T> } | null>(null);

  useEffect(() => {
    let atual = true;
    fonte.consultar(caminho, validar).then(
      (dados) => {
        if (atual) setUltimo({ chave, resultado: { fase: "pronto", dados } });
      },
      (erro: unknown) => {
        if (!atual || erro instanceof TokenRecusado) return;
        const resultado: Resultado<T> =
          erro instanceof AcessoNegado ? { fase: "negado" } : { fase: "erro" };
        setUltimo({ chave, resultado });
      },
    );
    return () => {
      atual = false;
    };
  }, [fonte, caminho, validar, chave]);

  // O resultado de outro caminho ou de outra tentativa não vale para este: ainda carregando.
  const estado: EstadoDoBloco<T> =
    ultimo?.chave === chave ? ultimo.resultado : { fase: "carregando" };
  return { estado, tentarDeNovo: () => setTentativa((n) => n + 1) };
}
