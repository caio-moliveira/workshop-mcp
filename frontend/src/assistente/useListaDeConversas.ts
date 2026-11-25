import { useCallback, useEffect, useRef, useState } from "react";

import {
  LISTA_CARREGANDO,
  listaAtualizada,
  listaComErro,
  listaRecebida,
  semAConversa,
  type ListaDeConversas,
} from "./listaDeConversas";
import type { FonteDoAssistente } from "./useConversa";

/**
 * A lista das conversas do usuário, pedida à API a cada vez que quem chama monta: abrir a visão
 * "Conversas" sempre mostra a lista atual, com o que outra aba gravou ou apagou. No modo
 * expandido a lista fica sempre montada, e quem chama a atualiza ao fim de cada resposta.
 */
export function useListaDeConversas(fonte: FonteDoAssistente): {
  lista: ListaDeConversas;
  /** A conversa que não pôde ser apagada, para avisar ao lado dela. */
  falhaAoApagar: string | null;
  recarregar: () => void;
  /** Pede a lista de novo sem tirá-la da tela: sem esqueleto, e uma falha mantém a antiga. */
  atualizar: () => void;
  apagar: (id: string) => Promise<boolean>;
} {
  const [lista, setLista] = useState<ListaDeConversas>(LISTA_CARREGANDO);
  const [falhaAoApagar, setFalhaAoApagar] = useState<string | null>(null);
  // Só a carga mais recente muda a lista: uma lenta que chega depois não a sobrescreve.
  const ultimaCarga = useRef(0);

  // Pede a lista e a troca quando chega. A lista já começa carregando: a primeira carga não
  // precisa marcar nada antes.
  const carregar = useCallback(async () => {
    const carga = ++ultimaCarga.current;
    let nova: ListaDeConversas;
    try {
      nova = listaRecebida(await fonte.listarConversas());
    } catch {
      nova = listaComErro();
    }
    if (carga === ultimaCarga.current) setLista((naTela) => listaAtualizada(naTela, nova));
  }, [fonte]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const recarregar = useCallback(() => {
    setLista(LISTA_CARREGANDO);
    void carregar();
  }, [carregar]);

  const atualizar = useCallback(() => {
    void carregar();
  }, [carregar]);

  /** Apaga na API e, só se deu certo, tira da lista. Devolve se apagou. */
  const apagar = useCallback(
    async (id: string) => {
      setFalhaAoApagar(null);
      try {
        await fonte.apagarConversa(id);
      } catch {
        setFalhaAoApagar(id);
        return false;
      }
      setLista((atual) => semAConversa(atual, id));
      return true;
    },
    [fonte],
  );

  return { lista, falhaAoApagar, recarregar, atualizar, apagar };
}
