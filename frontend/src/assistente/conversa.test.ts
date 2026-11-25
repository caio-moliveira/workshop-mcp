import { describe, expect, it } from "vitest";

import {
  CONVERSA_VAZIA,
  enviar,
  itensParaEnviar,
  parar,
  podeEnviar,
  receber,
  respondendo,
  type Conversa,
} from "./conversa";
import type { EventoDaResposta } from "./fluxo";
import { ITENS_DA_CONVERSA, LIMITE_DE_CARACTERES_DA_PERGUNTA } from "./limites";

describe("conversa", () => {
  it("ao enviar, guarda a pergunta e abre uma resposta ainda chegando", () => {
    const conversa = enviar(CONVERSA_VAZIA, "O que está causando os atrasos?");
    expect(conversa.falas).toEqual([
      { autor: "usuario", texto: "O que está causando os atrasos?" },
      { autor: "assistente", texto: "", situacao: "chegando", consultando: false },
    ]);
    expect(respondendo(conversa)).toBe(true);
  });

  const perguntada = enviar(CONVERSA_VAZIA, "O que está causando os atrasos?");

  function aplicar(conversa: Conversa, ...eventos: EventoDaResposta[]): Conversa {
    return eventos.reduce(receber, conversa);
  }

  function resposta(conversa: Conversa) {
    return conversa.falas.at(-1);
  }

  it("acumula os trechos na resposta", () => {
    const conversa = aplicar(
      perguntada,
      { tipo: "texto", texto: "Os atrasos " },
      { tipo: "texto", texto: "vêm de três lojistas." },
    );
    expect(resposta(conversa)).toMatchObject({
      texto: "Os atrasos vêm de três lojistas.",
      situacao: "chegando",
    });
  });

  it("marca a consulta aos dados até o próximo trecho", () => {
    const consultando = aplicar(
      perguntada,
      { tipo: "texto", texto: "Vou ver. " },
      { tipo: "estado" },
    );
    expect(resposta(consultando)).toMatchObject({ texto: "Vou ver. ", consultando: true });

    const depois = receber(consultando, { tipo: "texto", texto: "Achei." });
    expect(resposta(depois)).toMatchObject({ texto: "Vou ver. Achei.", consultando: false });
  });

  it("no fim, conclui a resposta e libera o envio", () => {
    const conversa = aplicar(
      perguntada,
      { tipo: "estado" },
      { tipo: "texto", texto: "Pronto." },
      { tipo: "fim" },
    );
    expect(resposta(conversa)).toEqual({
      autor: "assistente",
      texto: "Pronto.",
      situacao: "concluida",
      consultando: false,
    });
    expect(respondendo(conversa)).toBe(false);
    expect(podeEnviar(conversa, "e por lojista?")).toBe(true);
  });

  it("o fim com aviso conclui a resposta mantendo o texto e guarda o aviso", () => {
    const aviso = "A resposta parou aqui: a pergunta precisou de consultas demais.";
    const conversa = aplicar(perguntada, { tipo: "texto", texto: "Parcial" }, { tipo: "fim", aviso });
    expect(resposta(conversa)).toEqual({
      autor: "assistente",
      texto: "Parcial",
      situacao: "concluida",
      consultando: false,
      aviso,
    });
    expect(podeEnviar(conversa, "e por lojista?")).toBe(true);
  });

  it("depois de um erro, a nova pergunta abre outra resposta e a anterior fica como estava", () => {
    const comErro = aplicar(
      perguntada,
      { tipo: "texto", texto: "Parcial" },
      { tipo: "erro", mensagem: "Falhou." },
    );
    const conversa = enviar(comErro, "De novo?");
    expect(conversa.falas.slice(1)).toEqual([
      { autor: "assistente", texto: "Parcial", situacao: "erro", consultando: false, erro: "Falhou." },
      { autor: "usuario", texto: "De novo?" },
      { autor: "assistente", texto: "", situacao: "chegando", consultando: false },
    ]);
  });

  it("no erro, guarda a mensagem, mantém o texto recebido e libera o envio", () => {
    const mensagem = "O assistente está indisponível no momento. Tente de novo mais tarde.";
    const conversa = aplicar(
      perguntada,
      { tipo: "texto", texto: "Parcial" },
      { tipo: "estado" },
      { tipo: "erro", mensagem },
    );
    expect(resposta(conversa)).toEqual({
      autor: "assistente",
      texto: "Parcial",
      situacao: "erro",
      consultando: false,
      erro: mensagem,
    });
    expect(podeEnviar(conversa, "De novo?")).toBe(true);
  });

  it("bloqueia o envio enquanto a resposta chega", () => {
    const chegando = receber(perguntada, { tipo: "texto", texto: "Os" });
    expect(podeEnviar(chegando, "outra pergunta")).toBe(false);
    expect(enviar(chegando, "outra pergunta")).toBe(chegando);
  });

  it("não envia pergunta em branco", () => {
    expect(podeEnviar(CONVERSA_VAZIA, "  \n ")).toBe(false);
    expect(enviar(CONVERSA_VAZIA, "  ")).toBe(CONVERSA_VAZIA);
  });

  it("ignora eventos que chegam sem resposta em andamento", () => {
    const concluida = aplicar(perguntada, { tipo: "fim" });
    expect(receber(concluida, { tipo: "texto", texto: "atrasado" })).toBe(concluida);
    expect(receber(CONVERSA_VAZIA, { tipo: "estado" })).toBe(CONVERSA_VAZIA);
  });

  it("parar mantém o texto recebido, marca a resposta como interrompida e libera o envio", () => {
    const chegando = aplicar(
      perguntada,
      { tipo: "texto", texto: "Os atrasos " },
      { tipo: "estado" },
    );
    const parada = parar(chegando);
    expect(resposta(parada)).toEqual({
      autor: "assistente",
      texto: "Os atrasos ",
      situacao: "interrompida",
      consultando: false,
    });
    expect(respondendo(parada)).toBe(false);
    expect(podeEnviar(parada, "e por lojista?")).toBe(true);
    // O que ainda chegar daquela resposta não muda mais nada.
    expect(receber(parada, { tipo: "texto", texto: "vêm de" })).toBe(parada);
  });

  it("parar sem resposta em andamento não muda nada", () => {
    const concluida = aplicar(perguntada, { tipo: "fim" });
    expect(parar(concluida)).toBe(concluida);
  });

  it("a pergunta seguinte leva só as perguntas com resposta concluída, em ordem", () => {
    const comErro = "O assistente está indisponível no momento. Tente de novo mais tarde.";
    let conversa = aplicar(perguntada, { tipo: "texto", texto: "Três lojistas." }, { tipo: "fim" });
    conversa = aplicar(
      enviar(conversa, "Desde quando?"),
      { tipo: "texto", texto: "Desde" },
      { tipo: "erro", mensagem: comErro },
    );
    conversa = parar(receber(enviar(conversa, "Quais?"), { tipo: "texto", texto: "A Loja" }));
    conversa = aplicar(enviar(conversa, "Por estado?"), { tipo: "texto", texto: "SP." }, {
      tipo: "fim",
    });

    expect(itensParaEnviar(conversa)).toEqual([
      { autor: "usuario", texto: "O que está causando os atrasos?" },
      { autor: "assistente", texto: "Três lojistas." },
      { autor: "usuario", texto: "Por estado?" },
      { autor: "assistente", texto: "SP." },
    ]);
  });

  it("sem conversa anterior, a pergunta vai sozinha", () => {
    expect(itensParaEnviar(CONVERSA_VAZIA)).toEqual([]);
  });

  it("a pergunta seguinte entra depois da resposta anterior", () => {
    const conversa = enviar(
      aplicar(perguntada, { tipo: "texto", texto: "Três lojistas." }, { tipo: "fim" }),
      "e por estado?",
    );
    expect(conversa.falas.map((fala) => [fala.autor, fala.texto])).toEqual([
      ["usuario", "O que está causando os atrasos?"],
      ["assistente", "Três lojistas."],
      ["usuario", "e por estado?"],
      ["assistente", ""],
    ]);
  });

  function respondida(conversa: Conversa, pergunta: string, texto: string): Conversa {
    return aplicar(enviar(conversa, pergunta), { tipo: "texto", texto }, { tipo: "fim" });
  }

  it("numa conversa longa, leva só os pares mais recentes que cabem no teto de itens", () => {
    let conversa = CONVERSA_VAZIA;
    for (let n = 1; n <= 15; n++) conversa = respondida(conversa, `pergunta ${n}`, `resposta ${n}`);

    const itens = itensParaEnviar(conversa);
    expect(itens).toHaveLength(ITENS_DA_CONVERSA);
    expect(itens[0]).toEqual({ autor: "usuario", texto: "pergunta 6" });
    expect(itens.at(-1)).toEqual({ autor: "assistente", texto: "resposta 15" });
  });

  it("corta a resposta longa no teto de caracteres e marca o corte", () => {
    const longa = "📦".repeat(LIMITE_DE_CARACTERES_DA_PERGUNTA + 500);
    const [, item] = itensParaEnviar(respondida(CONVERSA_VAZIA, "Quais?", longa));

    expect([...item.texto]).toHaveLength(LIMITE_DE_CARACTERES_DA_PERGUNTA);
    expect(item.texto.startsWith("📦".repeat(100))).toBe(true);
    expect(item.texto.endsWith("…")).toBe(true);
  });

  it("a resposta no teto de caracteres vai inteira", () => {
    const noTeto = "a".repeat(LIMITE_DE_CARACTERES_DA_PERGUNTA);
    const [, item] = itensParaEnviar(respondida(CONVERSA_VAZIA, "Quais?", noTeto));
    expect(item.texto).toBe(noTeto);
  });
});
