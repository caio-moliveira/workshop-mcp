import { useEffect, useState, type ReactNode } from "react";

import type { UsuarioAutenticado } from "../api";
import { PainelDoAssistente } from "../assistente/PainelDoAssistente";
import { useConversa, type FonteDoAssistente } from "../assistente/useConversa";
import { usePodeExpandir } from "../assistente/usePodeExpandir";
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
 * não a apaga, e sair da sessão desmonta tudo. Pelo mesmo motivo, expandir e recolher o painel só
 * muda a forma dele, nunca a conversa.
 */
export function AppShell({ usuario, assistente, aoSair, children }: Propriedades) {
  const [navegacaoAberta, setNavegacaoAberta] = useState(false);
  const [assistenteAberto, setAssistenteAberto] = useState(false);
  const [expansaoPedida, setExpansaoPedida] = useState(false);
  // Estreitar a tela com o modo expandido aberto volta ao painel em tela cheia, sem fechá-lo.
  const podeExpandir = usePodeExpandir();
  const expandido = assistenteAberto && expansaoPedida && podeExpandir;
  const { conversa, abertura, perguntar, parar, abrir, comecarNovaConversa } =
    useConversa(assistente);

  useEffect(() => {
    if (!navegacaoAberta && !assistenteAberto) return;
    const fecharComEsc = (evento: KeyboardEvent) => {
      if (evento.key !== "Escape") return;
      setNavegacaoAberta(false);
      // Esc sai do modo expandido para o painel lateral; só o Esc seguinte fecha o assistente.
      if (expandido) setExpansaoPedida(false);
      else setAssistenteAberto(false);
    };
    window.addEventListener("keydown", fecharComEsc);
    return () => window.removeEventListener("keydown", fecharComEsc);
  }, [navegacaoAberta, assistenteAberto, expandido]);

  // Fechado, o assistente volta a abrir como painel lateral.
  function alternarAssistente() {
    setAssistenteAberto((aberto) => !aberto);
    setExpansaoPedida(false);
  }

  function fecharAssistente() {
    setAssistenteAberto(false);
    setExpansaoPedida(false);
  }

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
          aoAlternarAssistente={alternarAssistente}
          aoSair={aoSair}
        />
        {/* Coberta pelo modo expandido, a página sai do alcance do teclado e do leitor de tela. */}
        <main className={estilos.conteudo} inert={expandido}>
          {children}
        </main>
      </div>
      {assistenteAberto && (
        <PainelDoAssistente
          usuario={usuario}
          fonte={assistente}
          conversa={conversa}
          abertura={abertura}
          expandido={expandido}
          aoAlternarExpansao={podeExpandir ? () => setExpansaoPedida((atual) => !atual) : undefined}
          aoPerguntar={perguntar}
          aoParar={parar}
          aoAbrir={abrir}
          aoComecarNova={comecarNovaConversa}
          aoFechar={fecharAssistente}
        />
      )}
    </div>
  );
}
