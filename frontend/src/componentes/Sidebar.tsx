import type { CSSProperties, MouseEvent, ReactNode } from "react";

import type { UsuarioAutenticado } from "../api";
import { irPara, naPaginaDeSeguranca, PAGINA_DE_SEGURANCA, usePagina } from "../navegacao";
import { corDoPerfil, DESCRICAO_DOS_PERFIS } from "../perfis";
import { IconeEscudo, IconeFechar, IconePainel } from "./icones";
import { Marca } from "./Marca";
import { ProfileIndicator } from "./ProfileIndicator";
import estilos from "./Sidebar.module.css";

interface Propriedades {
  usuario: UsuarioAutenticado;
  /** No celular e no tablet a sidebar é uma gaveta; no desktop fica sempre visível. */
  aberta: boolean;
  aoFechar: () => void;
}

interface PropriedadesDoItem {
  href: string;
  atual: boolean;
  icone: ReactNode;
  aoNavegar: () => void;
  estilo?: CSSProperties;
  children: ReactNode;
}

/** Um item da navegação: troca de página sem recarregar, e abre em outra aba com Ctrl ou Cmd. */
function Item({ href, atual, icone, aoNavegar, estilo, children }: PropriedadesDoItem) {
  function navegar(evento: MouseEvent<HTMLAnchorElement>) {
    if (evento.button !== 0 || evento.metaKey || evento.ctrlKey || evento.shiftKey) return;
    evento.preventDefault();
    irPara(href);
    aoNavegar();
  }
  return (
    <a
      href={href}
      className={estilos.item}
      aria-current={atual ? "page" : undefined}
      style={estilo}
      onClick={navegar}
    >
      <span className={estilos.icone}>{icone}</span>
      {children}
    </a>
  );
}

/**
 * Navegação lateral (FE §5): o painel do perfil do usuário e, com o interruptor de demonstração
 * ligado, o painel de segurança, igual para os quatro perfis.
 */
export function Sidebar({ usuario, aberta, aoFechar }: Propriedades) {
  const perfil = DESCRICAO_DOS_PERFIS[usuario.perfil];
  const pagina = usePagina();
  const comSeguranca = usuario.painel_de_seguranca === true;
  const naSeguranca = naPaginaDeSeguranca(usuario, pagina);
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
        <Item
          href="/"
          atual={!naSeguranca}
          icone={<IconePainel />}
          aoNavegar={aoFechar}
          estilo={corDoPerfil(usuario.perfil)}
        >
          {perfil.rotuloDoPainel}
        </Item>
        {comSeguranca && (
          <Item
            href={PAGINA_DE_SEGURANCA}
            atual={naSeguranca}
            icone={<IconeEscudo />}
            aoNavegar={aoFechar}
          >
            Segurança
          </Item>
        )}
      </nav>

      <div className={estilos.rodape}>
        <ProfileIndicator perfil={usuario.perfil} nome={usuario.nome} />
      </div>
    </aside>
  );
}
