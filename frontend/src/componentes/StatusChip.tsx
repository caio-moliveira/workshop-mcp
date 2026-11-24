import estilos from "./StatusChip.module.css";

/** O que a situação quer dizer para o negócio: só a cor do ponto, nunca sozinha (o texto basta). */
export type TomDaSituacao = "sucesso" | "atencao" | "erro" | "informacao" | "neutro";

interface Propriedades {
  texto: string;
  tom: TomDaSituacao;
}

/** Situação em chip discreto, de baixo contraste, nunca badge saturada (FE §7, §12). */
export function StatusChip({ texto, tom }: Propriedades) {
  return (
    <span className={estilos.chip}>
      <span className={`${estilos.ponto} ${estilos[tom]}`} aria-hidden="true" />
      {texto}
    </span>
  );
}
