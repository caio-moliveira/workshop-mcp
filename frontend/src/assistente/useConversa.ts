import { useCallback, useEffect, useRef, useState } from "react";

import {
  carregar,
  comecarNova,
  CONVERSA_VAZIA,
  corpoDaPergunta,
  enviar,
  parar as pararResposta,
  podeEnviar,
  receber,
  type Conversa,
  type ConversaLida,
} from "./conversa";
import type { EventoDaResposta } from "./fluxo";
import type { ListaLida } from "./listaDeConversas";
import { mensagemDaFalha, type CorpoDaPergunta } from "./rede";

/** Quem leva a pergunta e os pedidos do histórico à API: a Sessao, que põe o token e cuida do 401. */
export interface FonteDoAssistente {
  /** Abortar o `sinal` fecha a conexão da resposta. */
  perguntar(corpo: CorpoDaPergunta, sinal?: AbortSignal): AsyncIterable<EventoDaResposta>;
  listarConversas(): Promise<ListaLida>;
  lerConversa(id: string): Promise<ConversaLida>;
  apagarConversa(id: string): Promise<void>;
}

/** Reabrir uma conversa do histórico: nada pedido, lendo, ou a leitura falhou. */
export type Abertura = { situacao: "pronta" } | { situacao: "abrindo" } | { situacao: "erro"; id: string };

const PRONTA: Abertura = { situacao: "pronta" };

/**
 * A conversa com o assistente, o envio de perguntas e a parada da resposta, mais reabrir uma
 * conversa do histórico e começar outra. Fica no estado de quem chama: enquanto ele estiver
 * montado, a conversa sobrevive a fechar o painel e a trocar de página. A conversa fica gravada na
 * API, mas o navegador não guarda nada, nem o identificador dela: recarregar ou sair abre uma
 * conversa nova.
 */
export function useConversa(fonte: FonteDoAssistente): {
  conversa: Conversa;
  abertura: Abertura;
  perguntar: (pergunta: string) => void;
  parar: () => void;
  abrir: (id: string) => void;
  comecarNovaConversa: () => void;
} {
  const [conversa, setConversa] = useState<Conversa>(CONVERSA_VAZIA);
  const [abertura, setAbertura] = useState<Abertura>(PRONTA);
  // A conexão da resposta em andamento, para parar.
  const emAndamento = useRef<AbortController | null>(null);
  // A última conversa pedida: uma leitura que chega depois de outro pedido não toma a tela.
  const pedida = useRef<string | null>(null);

  const perguntar = useCallback(
    (pergunta: string) => {
      if (!podeEnviar(conversa, pergunta)) return;
      const corpo = corpoDaPergunta(conversa, pergunta);
      const controle = new AbortController();
      emAndamento.current = controle;
      setConversa((atual) => enviar(atual, pergunta));
      void (async () => {
        try {
          for await (const evento of fonte.perguntar(corpo, controle.signal)) {
            // Parada: o que ainda chegar desta resposta não entra em outra.
            if (controle.signal.aborted) return;
            setConversa((atual) => receber(atual, evento));
          }
        } catch (erro) {
          if (controle.signal.aborted) return;
          const mensagem = mensagemDaFalha(erro);
          setConversa((atual) => receber(atual, { tipo: "erro", mensagem }));
        } finally {
          if (emAndamento.current === controle) emAndamento.current = null;
        }
      })();
    },
    [conversa, fonte],
  );

  const parar = useCallback(() => {
    emAndamento.current?.abort();
    emAndamento.current = null;
    setConversa(pararResposta);
  }, []);

  // Trocar de conversa abandona a resposta em andamento: ela fica gravada como interrompida.
  const abandonarResposta = useCallback(() => {
    emAndamento.current?.abort();
    emAndamento.current = null;
  }, []);

  const abrir = useCallback(
    (id: string) => {
      abandonarResposta();
      pedida.current = id;
      setAbertura({ situacao: "abrindo" });
      void (async () => {
        try {
          const lida = await fonte.lerConversa(id);
          if (pedida.current !== id) return;
          setConversa(carregar(lida));
          setAbertura(PRONTA);
        } catch {
          if (pedida.current !== id) return;
          setAbertura({ situacao: "erro", id });
        }
      })();
    },
    [abandonarResposta, fonte],
  );

  const comecarNovaConversa = useCallback(() => {
    abandonarResposta();
    pedida.current = null;
    setAbertura(PRONTA);
    setConversa(comecarNova());
  }, [abandonarResposta]);

  // Sair da sessão desmonta quem chama: a resposta em andamento é abandonada.
  useEffect(() => () => emAndamento.current?.abort(), []);

  return { conversa, abertura, perguntar, parar, abrir, comecarNovaConversa };
}
