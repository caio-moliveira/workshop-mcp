import { describe, expect, it } from "vitest";

import { buscaComPeriodo, lerPeriodo } from "./periodo";

describe("período na URL", () => {
  it.each(["30d", "90d", "12m", "24m"])("lê %s de ?periodo=", (periodo) => {
    expect(lerPeriodo(`?periodo=${periodo}`)).toBe(periodo);
  });

  it("sem período, vale 12 meses", () => {
    expect(lerPeriodo("")).toBe("12m");
    expect(lerPeriodo("?outro=1")).toBe("12m");
  });

  it.each(["?periodo=7d", "?periodo=", "?periodo=12M", "?periodo=%3Cscript%3E"])(
    "período inválido (%s) volta a 12 meses sem erro",
    (busca) => {
      expect(lerPeriodo(busca)).toBe("12m");
    },
  );

  it("troca o período na busca e mantém o resto", () => {
    expect(buscaComPeriodo("", "30d")).toBe("?periodo=30d");
    expect(buscaComPeriodo("?periodo=12m&x=1", "90d")).toBe("?periodo=90d&x=1");
  });
});
