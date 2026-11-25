import { useCallback, useState } from "react";

import { CONVERSA_VAZIA, enviar, podeEnviar, receber, type Conversa } from "./conversa";
import type { EventoDaResposta } from "./fluxo";
import { mensagemDaFalha, type CorpoDaPergunta } from "./rede";

/** Quem leva a pergunta à API: a Sessao, que põe o token e cuida do 401. */
export interface FonteDoAssistente {
  perguntar(corpo: CorpoDaPergunta): AsyncIterable<EventoDaResposta>;
}

/**
 * A conversa com o assistente e o envio de perguntas. Fica no estado de quem chama: enquanto ele
 * estiver montado, a conversa sobrevive a fechar o painel e a trocar de página.
 */
export function useConversa(fonte: FonteDoAssistente): {
  conversa: Conversa;
  perguntar: (pergunta: string) => void;
} {
  const [conversa, setConversa] = useState<Conversa>(CONVERSA_VAZIA);

  const perguntar = useCallback(
    (pergunta: string) => {
      if (!podeEnviar(conversa, pergunta)) return;
      setConversa((atual) => enviar(atual, pergunta));
      void (async () => {
        try {
          // Nesta entrega cada pergunta vai sozinha, sem a conversa anterior.
          for await (const evento of fonte.perguntar({ pergunta, conversa: [] })) {
            setConversa((atual) => receber(atual, evento));
          }
        } catch (erro) {
          const mensagem = mensagemDaFalha(erro);
          setConversa((atual) => receber(atual, { tipo: "erro", mensagem }));
        }
      })();
    },
    [conversa, fonte],
  );

  return { conversa, perguntar };
}
