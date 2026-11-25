import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiIndisponivel, TokenRecusado } from "../api";
import {
  ASSISTENTE_INDISPONIVEL,
  mensagemDaFalha,
  perguntarAoAssistente,
  SEM_RESPOSTA,
} from "./rede";

function responderCom(status: number, corpo: unknown) {
  responderComTexto(status, JSON.stringify(corpo));
}

function responderComTexto(status: number, corpo: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(corpo, { status })),
  );
}

async function falhaDaPergunta(): Promise<unknown> {
  try {
    await perguntarAoAssistente("http://api", "abc", { pergunta: "Oi?", conversa: [] });
  } catch (erro) {
    return erro;
  }
  throw new Error("a pergunta não falhou");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("falhas da pergunta antes do fluxo", () => {
  it("o 503 da rota vira o aviso com o texto que a API devolveu", async () => {
    const doServidor = "Texto do aviso escrito pela API.";
    responderCom(503, { erro: doServidor });

    expect(mensagemDaFalha(await falhaDaPergunta())).toBe(doServidor);
  });

  it("o 503 sem o texto no corpo vira o aviso de reserva", async () => {
    responderComTexto(503, "<html>Service Unavailable</html>");

    expect(mensagemDaFalha(await falhaDaPergunta())).toBe(ASSISTENTE_INDISPONIVEL);
  });

  it("o 401 segue como TokenRecusado, para a sessão tratar", async () => {
    responderCom(401, {});

    expect(await falhaDaPergunta()).toBeInstanceOf(TokenRecusado);
  });

  it("outra recusa, ou a rede fora, vira a mensagem genérica", async () => {
    responderCom(400, {});

    const erro = await falhaDaPergunta();
    expect(erro).toBeInstanceOf(ApiIndisponivel);
    expect(mensagemDaFalha(erro)).toBe(SEM_RESPOSTA);
  });
});
