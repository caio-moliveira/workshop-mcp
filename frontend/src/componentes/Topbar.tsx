import type { Eu } from "../api";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import { IconeMenu, IconeSair } from "./icones";
import { ProfileIndicator } from "./ProfileIndicator";
import estilos from "./Topbar.module.css";

interface Propriedades {
  eu: Eu;
  navegacaoAberta: boolean;
  aoAbrirNavegacao: () => void;
  aoSair: () => void;
}

/** Barra superior: contexto da área à esquerda, perfil e saída à direita (FE §5). */
export function Topbar({ eu, navegacaoAberta, aoAbrirNavegacao, aoSair }: Propriedades) {
  return (
    <header className={estilos.topbar}>
      <div className={estilos.contexto}>
        <button
          type="button"
          className={`${estilos.botaoDeIcone} ${estilos.menu}`}
          onClick={aoAbrirNavegacao}
          aria-label="Abrir navegação"
          aria-controls="sidebar"
          aria-expanded={navegacaoAberta}
        >
          <IconeMenu />
        </button>
        <nav aria-label="Você está em" className={estilos.trilha}>
          <span>pulso.</span>
          <span aria-hidden="true">/</span>
          <span className={estilos.atual}>{DESCRICAO_DOS_PERFIS[eu.perfil].nome}</span>
        </nav>
      </div>

      <div className={estilos.acoes}>
        <ProfileIndicator perfil={eu.perfil} />
        <button type="button" className={estilos.sair} onClick={aoSair}>
          <IconeSair />
          <span>Sair</span>
        </button>
      </div>
    </header>
  );
}
