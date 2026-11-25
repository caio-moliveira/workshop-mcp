import { afterEach, describe, expect, it, vi } from "vitest";

import { AcessoNegado, ApiIndisponivel, apagarNaApi, buscarDaApi, TokenRecusado } from "./api";

const eNumero = (valor: unknown): valor is number => typeof valor === "number";

function responderCom(status: number, corpo: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(corpo), { status })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("pedido a uma rota de dados", () => {
  it("manda o token e devolve o corpo validado", async () => {
    responderCom(200, 42);

    await expect(buscarDaApi("http://api", "abc", "/x?periodo=12m", eNumero)).resolves.toBe(42);
    expect(fetch).toHaveBeenCalledWith("http://api/x?periodo=12m", {
      headers: { Authorization: "Bearer abc" },
    });
  });

  it.each([
    [401, TokenRecusado],
    [403, AcessoNegado],
    [400, ApiIndisponivel],
    [503, ApiIndisponivel],
  ])("a resposta %i vira %o", async (status, erro) => {
    responderCom(status, { erro: "..." });

    await expect(buscarDaApi("http://api", "abc", "/x", eNumero)).rejects.toBeInstanceOf(erro);
  });

  it("resposta fora do contrato é erro, não dado", async () => {
    responderCom(200, "quarenta e dois");

    await expect(buscarDaApi("http://api", "abc", "/x", eNumero)).rejects.toBeInstanceOf(
      ApiIndisponivel,
    );
  });

  it("sem resposta da API é indisponibilidade", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );

    await expect(buscarDaApi("http://api", "abc", "/x", eNumero)).rejects.toBeInstanceOf(
      ApiIndisponivel,
    );
  });
});

describe("pedido para apagar", () => {
  it("manda DELETE com o token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 204 })),
    );

    await expect(apagarNaApi("http://api", "abc", "/conversas/c1")).resolves.toBeUndefined();
    expect(fetch).toHaveBeenCalledWith("http://api/conversas/c1", {
      method: "DELETE",
      headers: { Authorization: "Bearer abc" },
    });
  });

  it("o 404 também é sucesso: o que se queria apagar já não está lá (outra aba)", async () => {
    responderCom(404, { erro: "Conversa não encontrada." });

    await expect(apagarNaApi("http://api", "abc", "/conversas/c1")).resolves.toBeUndefined();
  });

  it.each([
    [401, TokenRecusado],
    [503, ApiIndisponivel],
  ])("a resposta %i vira %o", async (status, erro) => {
    responderCom(status, { erro: "..." });

    await expect(apagarNaApi("http://api", "abc", "/conversas/c1")).rejects.toBeInstanceOf(erro);
  });
});
