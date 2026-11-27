import { describe, expect, it } from "vitest";

import { naPaginaDeSeguranca, rotuloDaPagina } from "./navegacao";

const COM_O_PAINEL = { nome: "Diego Lima", perfil: "diretoria", painel_de_seguranca: true } as const;
const SEM_O_PAINEL = { nome: "Diego Lima", perfil: "diretoria" } as const;

describe("página de segurança", () => {
  it("só está aberta com o interruptor de demonstração ligado e o caminho dela", () => {
    expect(naPaginaDeSeguranca(COM_O_PAINEL, "/seguranca")).toBe(true);
    expect(naPaginaDeSeguranca(COM_O_PAINEL, "/")).toBe(false);
    expect(naPaginaDeSeguranca(SEM_O_PAINEL, "/seguranca")).toBe(false);
  });
});

describe("rótulo da página no caminho do topo", () => {
  it("na página de segurança, é Segurança", () => {
    expect(rotuloDaPagina(COM_O_PAINEL, "/seguranca")).toBe("Segurança");
  });

  it("no painel do perfil, é o nome do perfil", () => {
    expect(rotuloDaPagina(COM_O_PAINEL, "/")).toBe("Diretoria");
    expect(rotuloDaPagina({ nome: "Ana Ribeiro", perfil: "vendas" }, "/")).toBe("Vendas");
  });

  it("sem o painel de segurança, /seguranca mostra o painel do perfil e o nome dele", () => {
    expect(rotuloDaPagina(SEM_O_PAINEL, "/seguranca")).toBe("Diretoria");
  });
});
