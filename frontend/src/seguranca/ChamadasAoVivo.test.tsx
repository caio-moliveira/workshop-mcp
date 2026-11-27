import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { depoisDaBusca, type EstadoDasChamadasAoVivo } from "./aoVivo";
import { VisaoDasChamadasAoVivo } from "./ChamadasAoVivo";
import { eChamadasAoVivo, type ChamadaAoVivo } from "./contrato";

const NEGADA: ChamadaAoVivo = {
  horario: "2026-11-27T17:05:09+00:00",
  usuario: "ana.vendas",
  perfil: "vendas",
  ferramenta: "diretoria_indicadores",
  resultado: "negada",
};

const PERMITIDA: ChamadaAoVivo = {
  horario: "2026-11-27T17:04:58+00:00",
  usuario: "diego.diretoria",
  perfil: "diretoria",
  ferramenta: "diretoria_indicadores",
  resultado: "permitida",
};

function html(estado: EstadoDasChamadasAoVivo): string {
  return renderToStaticMarkup(<VisaoDasChamadasAoVivo estado={estado} />);
}

function linhas(marcacao: string): string[] {
  return marcacao.split("<tr").slice(1).filter((linha) => linha.includes("<td"));
}

describe("contrato das chamadas ao vivo", () => {
  it("aceita a lista, vazia ou com chamadas", () => {
    expect(eChamadasAoVivo({ chamadas: [] })).toBe(true);
    expect(eChamadasAoVivo({ chamadas: [NEGADA, PERMITIDA] })).toBe(true);
  });

  it("recusa desfecho, perfil ou horário fora do previsto", () => {
    expect(eChamadasAoVivo({ chamadas: [{ ...NEGADA, resultado: "recusada" }] })).toBe(false);
    expect(eChamadasAoVivo({ chamadas: [{ ...NEGADA, perfil: "financeiro" }] })).toBe(false);
    expect(eChamadasAoVivo({ chamadas: [{ ...NEGADA, horario: "ontem" }] })).toBe(false);
    expect(eChamadasAoVivo({ chamadas: [{ ...NEGADA, usuario: "" }] })).toBe(false);
    expect(eChamadasAoVivo({})).toBe(false);
  });
});

describe("estado depois de cada busca", () => {
  it("a lista nova substitui a anterior, sem atraso", () => {
    const anterior: EstadoDasChamadasAoVivo = {
      fase: "pronto",
      chamadas: [PERMITIDA],
      atrasado: true,
    };

    expect(depoisDaBusca(anterior, [NEGADA, PERMITIDA])).toEqual({
      fase: "pronto",
      chamadas: [NEGADA, PERMITIDA],
      atrasado: false,
    });
  });

  it("uma busca que falha mantém a última lista e a marca como atrasada", () => {
    const anterior: EstadoDasChamadasAoVivo = {
      fase: "pronto",
      chamadas: [PERMITIDA],
      atrasado: false,
    };

    expect(depoisDaBusca(anterior, null)).toEqual({ ...anterior, atrasado: true });
  });

  it("sem nenhuma lista ainda, a falha é o estado de erro", () => {
    expect(depoisDaBusca({ fase: "carregando" }, null)).toEqual({ fase: "erro" });
    expect(depoisDaBusca({ fase: "erro" }, [])).toEqual({
      fase: "pronto",
      chamadas: [],
      atrasado: false,
    });
  });
});

describe("bloco das chamadas ao vivo", () => {
  it("mostra cada chamada com a hora de Brasília, quem chamou, o perfil, a ferramenta e o desfecho", () => {
    const [negada, permitida] = linhas(
      html({ fase: "pronto", chamadas: [NEGADA, PERMITIDA], atrasado: false }),
    );

    expect(negada).toContain(">14:05:09<");
    expect(negada).toContain("ana.vendas");
    expect(negada).toContain("Vendas");
    expect(negada).toContain("diretoria_indicadores");
    expect(negada).toContain("Negada");
    expect(negada).toContain('data-resultado="negada"');
    expect(permitida).toContain("Permitida");
  });

  it("dá nome a cada desfecho da auditoria, com texto além da cor", () => {
    const marcacao = html({
      fase: "pronto",
      chamadas: [
        { ...NEGADA, resultado: "limitada" },
        { ...NEGADA, resultado: "parametro_invalido" },
        { ...NEGADA, resultado: "falha" },
      ],
      atrasado: false,
    });

    expect(marcacao).toContain("Barrada pelo limite");
    expect(marcacao).toContain("Parâmetro inválido");
    expect(marcacao).toContain("Falha");
  });

  it("sem chamadas, orienta a fazer uma pergunta", () => {
    const marcacao = html({ fase: "pronto", chamadas: [], atrasado: false });

    expect(marcacao).toContain("Nenhuma chamada ainda");
    expect(linhas(marcacao)).toEqual([]);
  });

  it("com a busca atrasada, avisa e mantém a última lista", () => {
    const marcacao = html({ fase: "pronto", chamadas: [NEGADA], atrasado: true });

    expect(marcacao).toContain("Sem atualização");
    expect(linhas(marcacao)).toHaveLength(1);
  });

  it("carregando e com erro, mantém o título do bloco", () => {
    expect(html({ fase: "carregando" })).toContain("Carregando as chamadas ao vivo");
    const erro = html({ fase: "erro" });
    expect(erro).toContain("Chamadas ao vivo");
    expect(erro).toContain("A auditoria não respondeu");
  });
});
