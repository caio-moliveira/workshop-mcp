import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DESCRICAO_DOS_PERFIS, PERFIS, type Perfil } from "../perfis";
import { PainelDoAssistente } from "./PainelDoAssistente";
import type { FonteDoAssistente } from "./useConversa";

const PERGUNTA = "Por que os clientes compram uma vez e não voltam?";

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

describe("a pergunta sugerida da Diretoria", () => {
  it("vazio, o assistente da Diretoria sugere a pergunta de por que os clientes não voltam", () => {
    expect(desenhar("diretoria")).toContain(PERGUNTA);
  });

  it.each(PERFIS.filter((perfil) => perfil !== "diretoria"))(
    "não aparece para o perfil %s",
    (perfil) => {
      expect(desenhar(perfil)).not.toContain(PERGUNTA);
    },
  );

  it("as perguntas sugeridas dos outros perfis não mudam", () => {
    expect(DESCRICAO_DOS_PERFIS.diretoria.perguntaSugerida).toBe(PERGUNTA);
    expect({
      vendas: DESCRICAO_DOS_PERFIS.vendas.perguntaSugerida,
      produtos: DESCRICAO_DOS_PERFIS.produtos.perguntaSugerida,
      comercial: DESCRICAO_DOS_PERFIS.comercial.perguntaSugerida,
    }).toEqual({
      vendas: "O que está causando os atrasos?",
      produtos: "Quais categorias concentram as piores notas?",
      comercial: "Qual canal traz os leads que mais convertem?",
    });
  });
});
