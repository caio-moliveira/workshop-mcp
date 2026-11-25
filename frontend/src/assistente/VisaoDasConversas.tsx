import { useState } from "react";

import { EmptyState } from "../componentes/EmptyState";
import { ErrorState } from "../componentes/ErrorState";
import { IconeLixeira } from "../componentes/icones";
import { formatarDataHora } from "../formatacao";
import { vazia } from "./listaDeConversas";
import type { FonteDoAssistente } from "./useConversa";
import { useListaDeConversas } from "./useListaDeConversas";
import estilos from "./VisaoDasConversas.module.css";

interface Propriedades {
  fonte: FonteDoAssistente;
  /** A conversa na tela, marcada na lista. */
  idAtual?: string;
  aoAbrir: (id: string) => void;
  /** A conversa apagada era a da tela: quem chama começa uma nova. */
  aoApagarAAtual: () => void;
}

/**
 * A visão "Conversas" do painel: as conversas do usuário, da mais recente para a mais antiga, para
 * reabrir ou apagar (RF-18), com os estados de carregamento, vazio e erro (FE §10).
 */
export function VisaoDasConversas({ fonte, idAtual, aoAbrir, aoApagarAAtual }: Propriedades) {
  const { lista, falhaAoApagar, recarregar, apagar } = useListaDeConversas(fonte);
  const [apagando, setApagando] = useState<string | null>(null);

  async function apagarConversa(id: string, titulo: string) {
    // Apagar é definitivo: confirma antes, como pede uma ação destrutiva (FE §10).
    if (!window.confirm(`Apagar a conversa "${titulo}"? Não dá para desfazer.`)) return;
    setApagando(id);
    const apagou = await apagar(id);
    setApagando(null);
    if (apagou && id === idAtual) aoApagarAAtual();
  }

  if (lista.situacao === "carregando") {
    return (
      <div className={estilos.carregando} role="status" aria-live="polite">
        <span className="visualmente-oculto">Carregando as conversas…</span>
        {[0, 1, 2, 3].map((linha) => (
          <span key={linha} className={estilos.esqueleto} aria-hidden="true" />
        ))}
      </div>
    );
  }
  if (lista.situacao === "erro") {
    return (
      <ErrorState
        variante="bloco"
        titulo="Não foi possível carregar as conversas"
        descricao="Tente de novo em instantes."
        acao="Tentar de novo"
        aoAcionar={recarregar}
      />
    );
  }
  if (vazia(lista)) {
    return (
      <EmptyState
        titulo="Nenhuma conversa ainda"
        descricao="As conversas com o assistente aparecem aqui assim que você fizer a primeira pergunta."
      />
    );
  }
  return (
    <ul className={estilos.lista} aria-label="Suas conversas">
      {lista.conversas.map((conversa) => (
        <li key={conversa.id} className={estilos.item}>
          <button
            type="button"
            className={estilos.abrir}
            aria-current={conversa.id === idAtual ? "true" : undefined}
            onClick={() => aoAbrir(conversa.id)}
          >
            <span className={estilos.titulo}>{conversa.titulo}</span>
            <span className={estilos.quando}>{formatarDataHora(conversa.ultimaAtividade)}</span>
          </button>
          <button
            type="button"
            className={estilos.apagar}
            disabled={apagando === conversa.id}
            aria-label={`Apagar a conversa "${conversa.titulo}"`}
            onClick={() => void apagarConversa(conversa.id, conversa.titulo)}
          >
            <IconeLixeira />
          </button>
          {falhaAoApagar === conversa.id && (
            <p className={estilos.falha} role="alert">
              Não foi possível apagar agora. Tente de novo.
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
