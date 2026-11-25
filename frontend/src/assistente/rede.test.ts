import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiIndisponivel, TokenRecusado } from "../api";
import {
  ASSISTENTE_INDISPONIVEL,
  mensagemDaFalha,
  perguntarAoAssistente,
  SEM_RESPOSTA,
} from "./rede";

function responderCom(status: number, corpo: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(corpo), { status })),
  );
}

async function falhaDaPergunta(): Promise<unknown> {
  try {
    for await (const evento of perguntarAoAssistente("http://api", "abc", {
      pergunta: "Oi?",
      conversa: [],
    })) {
      void evento;
    }
  } catch (erro) {
    return erro;
  }
  throw new Error("a pergunta não falhou");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("falhas da pergunta antes do fluxo", () => {
  it("o 503 da rota vira o aviso de assistente indisponível", async () => {
    responderCom(503, { erro: "O assistente está indisponível no momento." });

    expect(mensagemDaFalha(await falhaDaPergunta())).toBe(ASSISTENTE_INDISPONIVEL);
  });

  it("o 401 segue como TokenRecusado, para a sessão tratar", async () => {
    responderCom(401, { erro: "Não autenticado." });

    expect(await falhaDaPergunta()).toBeInstanceOf(TokenRecusado);
  });

  it("outra recusa, ou a rede fora, vira a mensagem genérica", async () => {
    responderCom(400, { erro: "Parâmetro inválido." });

    const erro = await falhaDaPergunta();
    expect(erro).toBeInstanceOf(ApiIndisponivel);
    expect(mensagemDaFalha(erro)).toBe(SEM_RESPOSTA);
  });
});
