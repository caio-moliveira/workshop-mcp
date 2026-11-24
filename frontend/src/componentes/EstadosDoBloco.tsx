import type { ReactNode } from "react";

import type { EstadoDoBloco } from "../useBloco";
import { DeniedState } from "./DeniedState";
import { ErrorState } from "./ErrorState";

/** Anuncia o carregamento aos leitores de tela; o esqueleto dentro dele fica só para a vista. */
export function AnuncioDeCarregamento({
  texto,
  className,
  children,
}: {
  texto: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={className} role="status" aria-live="polite">
      <span className="visualmente-oculto">{texto}</span>
      {children}
    </div>
  );
}

interface Propriedades<T> {
  estado: EstadoDoBloco<T>;
  tentarDeNovo: () => void;
  /** O conteúdo do bloco, por extenso, para a mensagem de erro: "os indicadores". */
  nome: string;
  /** O que aparece enquanto carrega, proporcional ao conteúdo, com o AnuncioDeCarregamento. */
  carregando: ReactNode;
  /** O bloco com os dados prontos, ou o estado vazio dele. */
  children: (dados: T) => ReactNode;
}

/**
 * Os estados que todo bloco do painel trata igual: carregando, erro com "Tentar de novo" e
 * negado (FE §10). O bloco cuida só dos dados prontos e do vazio.
 */
export function EstadosDoBloco<T>({
  estado,
  tentarDeNovo,
  nome,
  carregando,
  children,
}: Propriedades<T>) {
  switch (estado.fase) {
    case "carregando":
      return carregando;
    case "erro":
      return (
        <ErrorState
          variante="bloco"
          titulo={`Não foi possível carregar ${nome}`}
          descricao="O servidor não respondeu como esperado. Os outros blocos do painel não são afetados."
          acao="Tentar de novo"
          aoAcionar={tentarDeNovo}
        />
      );
    case "negado":
      return <DeniedState />;
    case "pronto":
      return children(estado.dados);
  }
}
