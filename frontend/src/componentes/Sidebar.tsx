import type { CSSProperties } from "react";

import type { Eu } from "../api";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import { IconeFechar, IconePainel } from "./icones";
import { Marca } from "./Marca";
import { ProfileIndicator } from "./ProfileIndicator";
import estilos from "./Sidebar.module.css";

interface Propriedades {
  eu: Eu;
  /** No celular e no tablet a sidebar é uma gaveta; no desktop fica sempre visível. */
  aberta: boolean;
  aoFechar: () => void;
}

/** Navegação lateral. Mostra só a área do perfil do usuário (FE §5). */
export function Sidebar({ eu, aberta, aoFechar }: Propriedades) {
  const perfil = DESCRICAO_DOS_PERFIS[eu.perfil];
  return (
    <aside
      id="sidebar"
      className={estilos.sidebar}
      data-aberta={aberta}
      aria-label="Navegação principal"
    >
      <div className={estilos.topo}>
        <Marca />
        <button
          type="button"
          className={estilos.fechar}
          onClick={aoFechar}
          aria-label="Fechar navegação"
        >
          <IconeFechar />
        </button>
      </div>

      <nav className={estilos.navegacao}>
        <a
          href="/"
          className={estilos.item}
          aria-current="page"
          style={{ "--cor-do-perfil": perfil.cor } as CSSProperties}
        >
          <span className={estilos.icone}>
            <IconePainel />
          </span>
          {perfil.area}
        </a>
      </nav>

      <div className={estilos.rodape}>
        <ProfileIndicator perfil={eu.perfil} nome={eu.nome} />
      </div>
    </aside>
  );
}
