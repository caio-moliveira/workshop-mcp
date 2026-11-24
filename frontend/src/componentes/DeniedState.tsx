import { useId } from "react";

import estilos from "./EmptyState.module.css";
import { IconeCadeado } from "./icones";

interface Propriedades {
  titulo?: string;
  descricao?: string;
}

/** A API negou o acesso (403): visual sério e neutro, sem alarme e sem pista dos dados (FE §10). */
export function DeniedState({
  titulo = "Acesso não disponível",
  descricao = "Seu perfil não tem acesso a estas informações. Se precisar delas, fale com quem administra o pulso.",
}: Propriedades) {
  const idDoTitulo = useId();
  return (
    <section className={estilos.vazio} aria-labelledby={idDoTitulo}>
      <span className={estilos.icone}>
        <IconeCadeado />
      </span>
      <h2 id={idDoTitulo} className={estilos.titulo}>
        {titulo}
      </h2>
      <p className={estilos.descricao}>{descricao}</p>
    </section>
  );
}
