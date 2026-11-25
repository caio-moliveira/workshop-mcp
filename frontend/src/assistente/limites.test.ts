import { describe, expect, it } from "vitest";

import { CONVERSA_VAZIA, enviar, podeEnviar } from "./conversa";
import { caracteresDaPergunta, LIMITE_DE_CARACTERES_DA_PERGUNTA, passouDoLimite } from "./limites";

describe("teto de caracteres da pergunta", () => {
  it("é o padrão do backend, 2.000 caracteres", () => {
    expect(LIMITE_DE_CARACTERES_DA_PERGUNTA).toBe(2000);
  });

  it("aceita a pergunta no teto e recusa a que passa dele", () => {
    expect(passouDoLimite("a".repeat(2000))).toBe(false);
    expect(passouDoLimite("a".repeat(2001))).toBe(true);
  });

  it("conta caracteres como o backend, não unidades UTF-16", () => {
    // Cada emoji é 1 caractere para o Python e 2 unidades para o JavaScript.
    expect(caracteresDaPergunta("📦".repeat(2000))).toBe(2000);
    expect(passouDoLimite("📦".repeat(2000))).toBe(false);
  });

  it("não conta os espaços das pontas, que não são enviados", () => {
    expect(passouDoLimite(`  ${"a".repeat(2000)}\n`)).toBe(false);
  });

  it("a pergunta acima do teto não é enviada", () => {
    const longa = "a".repeat(2001);
    expect(podeEnviar(CONVERSA_VAZIA, longa)).toBe(false);
    expect(enviar(CONVERSA_VAZIA, longa)).toBe(CONVERSA_VAZIA);
  });
});
