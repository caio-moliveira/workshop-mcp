import { describe, expect, it } from "vitest";

import {
  agruparPorGrupo,
  eCenarioDeSeguranca,
  eExecucaoDeAceite,
  eInstante,
  eMatrizCompleta,
  ePainelDeSeguranca,
} from "./contrato";
import { cenario, execucao, PERMITIDO } from "./exemplos";

describe("ePainelDeSeguranca", () => {
  it("aceita o estado vazio, sem execução gravada", () => {
    expect(ePainelDeSeguranca({ execucao: null })).toBe(true);
  });

  it("aceita uma execução com um cenário negado e um permitido", () => {
    expect(ePainelDeSeguranca({ execucao: execucao([cenario(), PERMITIDO]) })).toBe(true);
  });

  it("recusa a resposta sem a chave da execução", () => {
    expect(ePainelDeSeguranca({})).toBe(false);
    expect(ePainelDeSeguranca(null)).toBe(false);
  });
});

describe("eExecucaoDeAceite", () => {
  it("recusa um resumo que não bate com os cenários", () => {
    const valor = { ...execucao(), resumo: { ...execucao().resumo, executados: 3 } };
    expect(eExecucaoDeAceite(valor)).toBe(false);
  });

  it("recusa um resumo cujos permitidos e negados não somam os executados", () => {
    const valor = { ...execucao(), resumo: { executados: 1, permitidos: 1, negados: 1, divergencias: 0 } };
    expect(eExecucaoDeAceite(valor)).toBe(false);
  });

  it("recusa a data da execução fora do formato", () => {
    expect(eExecucaoDeAceite({ ...execucao(), executada_em: "ontem" })).toBe(false);
    expect(eExecucaoDeAceite({ ...execucao(), executada_em: "2026-11-26" })).toBe(false);
  });

  it("aceita a matriz completa com a data própria", () => {
    const matriz = {
      executada_em: "2026-11-25T10:00:00+00:00",
      pares: 132,
      permitidos: 33,
      negados: 99,
      divergencias: 0,
    };
    expect(eExecucaoDeAceite({ ...execucao(), matriz_completa: matriz })).toBe(true);
    expect(eMatrizCompleta({ ...matriz, negados: 98 })).toBe(false);
  });

  it("aceita a conferência da carga", () => {
    const carga = { confere: true, data_de_referencia: "2026-11-30", detalhe: null };
    expect(eExecucaoDeAceite({ ...execucao(), carga })).toBe(true);
    expect(eExecucaoDeAceite({ ...execucao(), carga: { confere: "sim" } })).toBe(false);
  });
});

describe("eCenarioDeSeguranca", () => {
  it("aceita um cenário com a linha da auditoria", () => {
    const auditoria = {
      id: 812,
      horario: "2026-11-26T14:03:13+00:00",
      usuario: "ana.vendas",
      ferramenta: "diretoria_indicadores",
      argumentos: { periodo: "12m" },
      resultado: "negada",
    };
    expect(eCenarioDeSeguranca(cenario({ auditoria, camadas_de_defesa: ["lista_de_ferramentas", "chamada"], grupo: "chamada" }))).toBe(true);
  });

  it("recusa um permitido com mensagem: ela poderia ser dado de negócio", () => {
    const comMensagem = { ...PERMITIDO, resposta: { status: 200, mensagem: "R$ 1.000", linhas: 1 } };
    expect(eCenarioDeSeguranca(comMensagem)).toBe(false);
  });

  it("recusa uma camada de defesa desconhecida ou nenhuma camada", () => {
    expect(eCenarioDeSeguranca({ ...cenario(), camadas_de_defesa: ["firewall"] })).toBe(false);
    expect(eCenarioDeSeguranca({ ...cenario(), camadas_de_defesa: [] })).toBe(false);
  });

  it("recusa um grupo, um desfecho ou um perfil fora dos previstos", () => {
    expect(eCenarioDeSeguranca({ ...cenario(), grupo: "rede" })).toBe(false);
    expect(eCenarioDeSeguranca({ ...cenario(), obtido: "talvez" })).toBe(false);
    expect(eCenarioDeSeguranca({ ...cenario(), perfil: "rh" })).toBe(false);
  });

  it("aceita um cenário sem perfil, de um token sem usuário", () => {
    const semToken = cenario({
      grupo: "token",
      camadas_de_defesa: ["token"],
      perfil: null,
      quem: { tipo: "token", nome: "sem token" },
      resposta: { status: 401, mensagem: null, linhas: null },
    });
    expect(eCenarioDeSeguranca(semToken)).toBe(true);
  });
});

describe("eInstante", () => {
  it("aceita a data e a hora com fuso e recusa uma data só", () => {
    expect(eInstante("2026-11-26T20:58:42.310935+00:00")).toBe(true);
    expect(eInstante("2026-11-26")).toBe(false);
    expect(eInstante(20261126)).toBe(false);
  });
});

describe("agruparPorGrupo", () => {
  it("agrupa na ordem das camadas de defesa e deixa fora os grupos vazios", () => {
    const assistente = cenario({ id: "a", grupo: "assistente", camadas_de_defesa: ["chamada"] });
    const token = cenario({ id: "t", grupo: "token", camadas_de_defesa: ["token"] });
    const api = cenario({ id: "p" });

    const grupos = agruparPorGrupo([assistente, api, token]);

    expect(grupos.map((g) => g.grupo)).toEqual(["token", "api", "assistente"]);
    expect(grupos[1]?.cenarios.map((c) => c.id)).toEqual(["p"]);
  });
});
