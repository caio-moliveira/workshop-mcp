import { describe, expect, it } from "vitest";

import { abrirGaveta, type Focavel } from "./teclado";

/** Um elemento que registra quando recebe o foco. */
function elemento(nome: string, focos: string[], conectado = true): Focavel {
  return { focus: () => focos.push(nome), isConnected: conectado };
}

function tecla(key: string): Event {
  return Object.assign(new Event("keydown"), { key });
}

describe("teclado da gaveta lateral", () => {
  it("ao abrir, o foco vai para a gaveta", () => {
    const focos: string[] = [];
    abrirGaveta(new EventTarget(), elemento("gaveta", focos), elemento("linha", focos), () => {});

    expect(focos).toEqual(["gaveta"]);
  });

  it("Esc fecha a gaveta; outra tecla não", () => {
    const teclado = new EventTarget();
    let fechou = 0;
    abrirGaveta(teclado, elemento("gaveta", []), null, () => (fechou += 1));

    teclado.dispatchEvent(tecla("Enter"));
    expect(fechou).toBe(0);
    teclado.dispatchEvent(tecla("Escape"));
    expect(fechou).toBe(1);
  });

  it("ao fechar, o foco volta à linha que abriu a gaveta, e o Esc deixa de ser ouvido", () => {
    const teclado = new EventTarget();
    const focos: string[] = [];
    let fechou = 0;
    const fechar = abrirGaveta(
      teclado,
      elemento("gaveta", focos),
      elemento("linha", focos),
      () => (fechou += 1),
    );

    fechar();
    teclado.dispatchEvent(tecla("Escape"));

    expect(focos).toEqual(["gaveta", "linha"]);
    expect(fechou).toBe(0);
  });

  it("uma linha que saiu da página não recebe o foco", () => {
    const focos: string[] = [];
    const fechar = abrirGaveta(
      new EventTarget(),
      elemento("gaveta", focos),
      elemento("linha", focos, false),
      () => {},
    );

    fechar();

    expect(focos).toEqual(["gaveta"]);
  });
});
