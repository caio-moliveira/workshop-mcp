import { useEffect, useState, type ReactNode } from "react";

import type { Eu } from "../api";
import estilos from "./AppShell.module.css";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface Propriedades {
  eu: Eu;
  aoSair: () => void;
  children: ReactNode;
}

/** Estrutura global da aplicação: sidebar, topbar e a área de conteúdo (FE §5). */
export function AppShell({ eu, aoSair, children }: Propriedades) {
  const [navegacaoAberta, setNavegacaoAberta] = useState(false);

  useEffect(() => {
    if (!navegacaoAberta) return;
    const fecharComEsc = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") setNavegacaoAberta(false);
    };
    window.addEventListener("keydown", fecharComEsc);
    return () => window.removeEventListener("keydown", fecharComEsc);
  }, [navegacaoAberta]);

  return (
    <div className={estilos.shell}>
      <Sidebar eu={eu} aberta={navegacaoAberta} aoFechar={() => setNavegacaoAberta(false)} />
      {navegacaoAberta && (
        <div
          className={estilos.fundo}
          onClick={() => setNavegacaoAberta(false)}
          aria-hidden="true"
        />
      )}
      <div className={estilos.principal}>
        <Topbar
          eu={eu}
          navegacaoAberta={navegacaoAberta}
          aoAbrirNavegacao={() => setNavegacaoAberta(true)}
          aoSair={aoSair}
        />
        <main className={estilos.conteudo}>{children}</main>
      </div>
    </div>
  );
}
