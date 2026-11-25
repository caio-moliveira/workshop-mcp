import { useEffect, useState, type ReactNode } from "react";

import type { UsuarioAutenticado } from "../api";
import { PainelDoAssistente } from "../assistente/PainelDoAssistente";
import { useConversa, type FonteDoAssistente } from "../assistente/useConversa";
import estilos from "./AppShell.module.css";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface Propriedades {
  usuario: UsuarioAutenticado;
  assistente: FonteDoAssistente;
  aoSair: () => void;
  children: ReactNode;
}

/**
 * Estrutura global da aplicação: sidebar, topbar, a área de conteúdo (FE §5) e o painel do
 * assistente (FE §8). A conversa vive aqui, acima das páginas: fechar o painel ou trocar de página
 * não a apaga, e sair da sessão desmonta tudo.
 */
export function AppShell({ usuario, assistente, aoSair, children }: Propriedades) {
  const [navegacaoAberta, setNavegacaoAberta] = useState(false);
  const [assistenteAberto, setAssistenteAberto] = useState(false);
  const { conversa, perguntar, parar } = useConversa(assistente);

  useEffect(() => {
    if (!navegacaoAberta && !assistenteAberto) return;
    const fecharComEsc = (evento: KeyboardEvent) => {
      if (evento.key !== "Escape") return;
      setNavegacaoAberta(false);
      setAssistenteAberto(false);
    };
    window.addEventListener("keydown", fecharComEsc);
    return () => window.removeEventListener("keydown", fecharComEsc);
  }, [navegacaoAberta, assistenteAberto]);

  return (
    <div className={estilos.shell}>
      <Sidebar
        usuario={usuario}
        aberta={navegacaoAberta}
        aoFechar={() => setNavegacaoAberta(false)}
      />
      {navegacaoAberta && (
        <div
          className={estilos.fundo}
          onClick={() => setNavegacaoAberta(false)}
          aria-hidden="true"
        />
      )}
      <div className={estilos.principal}>
        <Topbar
          usuario={usuario}
          navegacaoAberta={navegacaoAberta}
          assistenteAberto={assistenteAberto}
          aoAbrirNavegacao={() => setNavegacaoAberta(true)}
          aoAlternarAssistente={() => setAssistenteAberto((aberto) => !aberto)}
          aoSair={aoSair}
        />
        <main className={estilos.conteudo}>{children}</main>
      </div>
      {assistenteAberto && (
        <PainelDoAssistente
          usuario={usuario}
          conversa={conversa}
          aoPerguntar={perguntar}
          aoParar={parar}
          aoFechar={() => setAssistenteAberto(false)}
        />
      )}
    </div>
  );
}
