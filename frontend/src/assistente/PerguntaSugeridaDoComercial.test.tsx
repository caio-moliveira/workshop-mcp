import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DESCRICAO_DOS_PERFIS, PERFIS, type Perfil } from "../perfis";
import { PainelDoAssistente } from "./PainelDoAssistente";
import type { FonteDoAssistente } from "./useConversa";

const PERGUNTA = "Qual canal traz os leads que mais convertem?";

const FONTE: FonteDoAssistente = {
  // eslint-disable-next-line require-yield
  async *perguntar() {
    return;
  },
  listarConversas: () => new Promise(() => {}),
  lerConversa: () => new Promise(() => {}),
  apagarConversa: () => Promise.resolve(),
};

const SEM_ACAO = () => {};

/** O painel do assistente, vazio, para um usuário do perfil dado. */
function desenhar(perfil: Perfil): string {
  return renderToStaticMarkup(
    <PainelDoAssistente
      usuario={{ nome: "Carla", perfil }}
      fonte={FONTE}
      conversa={{ perguntasERespostas: [] }}
      abertura={{ situacao: "pronta" }}
      expandido={false}
      aoAlternarExpansao={SEM_ACAO}
      aoPerguntar={SEM_ACAO}
      aoParar={SEM_ACAO}
      aoAbrir={SEM_ACAO}
      aoComecarNova={SEM_ACAO}
      aoFechar={SEM_ACAO}
      aoTerminarResposta={() => SEM_ACAO}
    />,
  );
}

describe("a pergunta sugerida do Comercial", () => {
  it("vazio, o assistente do Comercial sugere a pergunta dos canais que mais convertem", () => {
    expect(desenhar("comercial")).toContain(PERGUNTA);
  });

  it.each(PERFIS.filter((perfil) => perfil !== "comercial"))(
    "não aparece para o perfil %s",
    (perfil) => {
      expect(desenhar(perfil)).not.toContain(PERGUNTA);
    },
  );

  it("diz canal e leads, nunca origem", () => {
    expect(DESCRICAO_DOS_PERFIS.comercial.perguntaSugerida).toBe(PERGUNTA);
    for (const perfil of PERFIS) {
      expect(DESCRICAO_DOS_PERFIS[perfil].perguntaSugerida?.toLowerCase() ?? "").not.toContain(
        "origem",
      );
    }
  });
});
