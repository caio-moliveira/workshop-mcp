import type { UsuarioAutenticado } from "../api";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import { IconeAssistente, IconeMenu, IconeSair } from "./icones";
import { ProfileIndicator } from "./ProfileIndicator";
import estilos from "./Topbar.module.css";

interface Propriedades {
  usuario: UsuarioAutenticado;
  navegacaoAberta: boolean;
  assistenteAberto: boolean;
  aoAlternarAssistente: () => void;
  aoAbrirNavegacao: () => void;
  aoSair: () => void;
}

/** Barra superior: contexto do perfil à esquerda; assistente, perfil e saída à direita (FE §5). */
export function Topbar({
  usuario,
  navegacaoAberta,
  assistenteAberto,
  aoAbrirNavegacao,
  aoAlternarAssistente,
  aoSair,
}: Propriedades) {
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
          <span className={estilos.atual}>{DESCRICAO_DOS_PERFIS[usuario.perfil].nome}</span>
        </nav>
      </div>

      <div className={estilos.acoes}>
        <button
          type="button"
          className={estilos.assistente}
          onClick={aoAlternarAssistente}
          aria-controls="assistente"
          aria-expanded={assistenteAberto}
        >
          <IconeAssistente />
          <span>Assistente</span>
        </button>
        <ProfileIndicator perfil={usuario.perfil} />
        <button type="button" className={estilos.sair} onClick={aoSair}>
          <IconeSair />
          <span>Sair</span>
        </button>
      </div>
    </header>
  );
}
