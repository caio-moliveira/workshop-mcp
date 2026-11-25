import { useCallback, useEffect, useRef, useState } from "react";

import {
  CONVERSA_VAZIA,
  corpoDaPergunta,
  enviar,
  parar as pararResposta,
  podeEnviar,
  receber,
  type Conversa,
} from "./conversa";
import type { EventoDaResposta } from "./fluxo";
import { mensagemDaFalha, type CorpoDaPergunta } from "./rede";

/** Quem leva a pergunta à API: a Sessao, que põe o token e cuida do 401. */
export interface FonteDoAssistente {
  /** Abortar o `sinal` fecha a conexão da resposta. */
  perguntar(corpo: CorpoDaPergunta, sinal?: AbortSignal): AsyncIterable<EventoDaResposta>;
}

/**
 * A conversa com o assistente, o envio de perguntas e a parada da resposta. Fica no estado de quem
 * chama: enquanto ele estiver montado, a conversa sobrevive a fechar o painel e a trocar de
 * página. A conversa fica gravada na API, mas o navegador não guarda nada, nem o identificador
 * dela: recarregar ou sair abre uma conversa nova.
 */
export function useConversa(fonte: FonteDoAssistente): {
  conversa: Conversa;
  perguntar: (pergunta: string) => void;
  parar: () => void;
} {
  const [conversa, setConversa] = useState<Conversa>(CONVERSA_VAZIA);
  // A conexão da resposta em andamento, para parar.
  const emAndamento = useRef<AbortController | null>(null);

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

  // Sair da sessão desmonta quem chama: a resposta em andamento é abandonada.
  useEffect(() => () => emAndamento.current?.abort(), []);

  return { conversa, perguntar, parar };
}
