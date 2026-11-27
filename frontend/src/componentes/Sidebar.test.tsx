import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { UsuarioAutenticado } from "../api";
import { Sidebar } from "./Sidebar";

function html(usuario: UsuarioAutenticado): string {
  return renderToStaticMarkup(<Sidebar usuario={usuario} aberta={false} aoFechar={() => {}} />);
}

function itens(marcacao: string): string[] {
  return [...marcacao.matchAll(/<a [^>]*href="([^"]+)"/g)].map((m) => m[1] ?? "");
}

describe("barra lateral", () => {
  it("com o painel de segurança ligado, traz o item Segurança abaixo do painel do perfil", () => {
    const marcacao = html({ nome: "Ana Ribeiro", perfil: "vendas", painel_de_seguranca: true });

    expect(itens(marcacao)).toEqual(["/", "/seguranca"]);
    expect(marcacao).toContain("Segurança");
  });

  it("o item Segurança é o mesmo para os quatro perfis", () => {
    for (const perfil of ["vendas", "produtos", "comercial", "diretoria"] as const) {
      const marcacao = html({ nome: "Alguém", perfil, painel_de_seguranca: true });
      expect(itens(marcacao)).toContain("/seguranca");
    }
  });

  it("sem o painel de segurança, mostra só o painel do perfil", () => {
    const marcacao = html({ nome: "Ana Ribeiro", perfil: "vendas" });

    expect(itens(marcacao)).toEqual(["/"]);
    expect(marcacao).not.toContain("Segurança");
  });
});
