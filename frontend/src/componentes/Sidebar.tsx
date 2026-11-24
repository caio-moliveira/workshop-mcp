import type { UsuarioAutenticado } from "../api";
import { corDoPerfil, DESCRICAO_DOS_PERFIS } from "../perfis";
import { IconeFechar, IconePainel } from "./icones";
import { Marca } from "./Marca";
import { ProfileIndicator } from "./ProfileIndicator";
import estilos from "./Sidebar.module.css";

interface Propriedades {
  usuario: UsuarioAutenticado;
  /** No celular e no tablet a sidebar é uma gaveta; no desktop fica sempre visível. */
  aberta: boolean;
  aoFechar: () => void;
}

/** Navegação lateral. Mostra só o painel do perfil do usuário (FE §5). */
export function Sidebar({ usuario, aberta, aoFechar }: Propriedades) {
  const perfil = DESCRICAO_DOS_PERFIS[usuario.perfil];
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
          style={corDoPerfil(usuario.perfil)}
        >
          <span className={estilos.icone}>
            <IconePainel />
          </span>
          {perfil.rotuloDoPainel}
        </a>
      </nav>

      <div className={estilos.rodape}>
        <ProfileIndicator perfil={usuario.perfil} nome={usuario.nome} />
      </div>
    </aside>
  );
}
