import { describe, expect, it } from "vitest";

import {
  carregar,
  comecarNova,
  CONVERSA_VAZIA,
  corpoDaPergunta,
  eConversaLida,
  enviar,
  parar,
  podeEnviar,
  receber,
  respondendo,
  type Conversa,
  type ConversaLida,
  type PerguntaOuResposta,
} from "./conversa";
import type { ChamadaDoRastreio, EventoDaResposta } from "./fluxo";

describe("conversa", () => {
  it("ao enviar, guarda a pergunta e abre uma resposta ainda chegando", () => {
    const conversa = enviar(CONVERSA_VAZIA, "O que está causando os atrasos?");
    expect(conversa.perguntasERespostas).toEqual([
      { autor: "usuario", texto: "O que está causando os atrasos?" },
      { autor: "assistente", texto: "", situacao: "chegando", consultando: false, rastreio: [] },
    ]);
    expect(respondendo(conversa)).toBe(true);
  });

  const perguntada = enviar(CONVERSA_VAZIA, "O que está causando os atrasos?");

  function aplicar(conversa: Conversa, ...eventos: EventoDaResposta[]): Conversa {
    return eventos.reduce(receber, conversa);
  }

  function resposta(conversa: Conversa) {
    return conversa.perguntasERespostas.at(-1);
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
      rastreio: [],
    });
    expect(respondendo(conversa)).toBe(false);
    expect(podeEnviar(conversa, "e por lojista?")).toBe(true);
  });

  it("o fim com aviso conclui a resposta mantendo o texto e guarda o aviso", () => {
    const aviso = "Aviso do fim, escrito pela API.";
    const conversa = aplicar(perguntada, { tipo: "texto", texto: "Parcial" }, { tipo: "fim", aviso });
    expect(resposta(conversa)).toEqual({
      autor: "assistente",
      texto: "Parcial",
      situacao: "concluida",
      consultando: false,
      rastreio: [],
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
    expect(conversa.perguntasERespostas.slice(1)).toEqual([
      {
        autor: "assistente",
        texto: "Parcial",
        situacao: "erro",
        consultando: false,
        erro: "Falhou.",
        rastreio: [],
      },
      { autor: "usuario", texto: "De novo?" },
      { autor: "assistente", texto: "", situacao: "chegando", consultando: false, rastreio: [] },
    ]);
  });

  it("no erro, guarda a mensagem, mantém o texto recebido e libera o envio", () => {
    const mensagem = "Mensagem de erro, escrita pela API.";
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
      rastreio: [],
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
      rastreio: [],
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

  const DA_CONVERSA: EventoDaResposta = {
    tipo: "conversa",
    idDaConversa: "conversa-1",
    idDaPergunta: "pergunta-1",
  };

  it("o evento da conversa guarda a conversa gravada e a pergunta na resposta", () => {
    const conversa = receber(perguntada, DA_CONVERSA);
    expect(conversa.id).toBe("conversa-1");
    expect(resposta(conversa)).toEqual({
      autor: "assistente",
      texto: "",
      situacao: "chegando",
      consultando: false,
      rastreio: [],
      idDaPergunta: "pergunta-1",
    });
  });

  it("a primeira pergunta vai sem conversa: a API abre uma nova", () => {
    expect(corpoDaPergunta(CONVERSA_VAZIA, "O que está causando os atrasos?")).toEqual({
      pergunta: "O que está causando os atrasos?",
    });
  });

  it("a pergunta seguinte leva só o identificador da conversa, nunca a conversa", () => {
    const conversa = aplicar(perguntada, DA_CONVERSA, { tipo: "texto", texto: "Três." }, {
      tipo: "fim",
    });
    expect(corpoDaPergunta(conversa, "e por lojista?")).toEqual({
      pergunta: "e por lojista?",
      id_da_conversa: "conversa-1",
    });
  });

  it("a conversa gravada continua depois de uma resposta com erro ou parada", () => {
    const comErro = aplicar(perguntada, DA_CONVERSA, { tipo: "erro", mensagem: "Falhou." });
    const parada = parar(receber(enviar(comErro, "De novo?"), { tipo: "texto", texto: "A" }));
    expect(corpoDaPergunta(parada, "Mais uma?")).toEqual({
      pergunta: "Mais uma?",
      id_da_conversa: "conversa-1",
    });
  });

  it("a nova pergunta não perde a conversa gravada", () => {
    const concluida = aplicar(perguntada, DA_CONVERSA, { tipo: "fim" });
    expect(enviar(concluida, "e por estado?").id).toBe("conversa-1");
  });

  const VENDAS_ATRASOS: ChamadaDoRastreio = {
    ferramenta: "vendas_atrasos",
    desfecho: "concluida",
    milissegundos: 182,
  };
  const EXPORTAR_TUDO: ChamadaDoRastreio = {
    ferramenta: "exportar_tudo",
    desfecho: "nao_concluida",
    milissegundos: 3,
  };
  const CONCLUIDA: EventoDaResposta = { tipo: "chamada", ...VENDAS_ATRASOS };
  const NEGADA: EventoDaResposta = { tipo: "chamada", ...EXPORTAR_TUDO };

  function rastreio(item: PerguntaOuResposta | undefined) {
    return item?.autor === "assistente" ? item.rastreio : undefined;
  }

  it("a resposta nasce sem chamadas no rastreio", () => {
    expect(rastreio(resposta(perguntada))).toEqual([]);
  });

  it("acumula as chamadas no rastreio da resposta, em ordem, sem mudar o texto", () => {
    const conversa = aplicar(
      perguntada,
      DA_CONVERSA,
      { tipo: "estado" },
      CONCLUIDA,
      NEGADA,
      { tipo: "texto", texto: "Três rotas." },
      { tipo: "fim" },
    );
    expect(resposta(conversa)).toMatchObject({
      texto: "Três rotas.",
      situacao: "concluida",
      idDaPergunta: "pergunta-1",
    });
    // Só a chamada, sem o tipo do evento.
    expect(rastreio(resposta(conversa))).toEqual([VENDAS_ATRASOS, EXPORTAR_TUDO]);
  });

  it("o rastreio da resposta anterior não passa para a seguinte", () => {
    const primeira = aplicar(perguntada, DA_CONVERSA, CONCLUIDA, { tipo: "fim" });
    const segunda = aplicar(enviar(primeira, "E por lojista?"), NEGADA, { tipo: "fim" });
    const [, anterior, , atual] = segunda.perguntasERespostas;
    expect(rastreio(anterior)).toEqual([VENDAS_ATRASOS]);
    expect(rastreio(atual)).toEqual([EXPORTAR_TUDO]);
  });

  it("a resposta parada guarda as chamadas que já tinham terminado", () => {
    const conversa = parar(aplicar(perguntada, DA_CONVERSA, CONCLUIDA));
    expect(resposta(conversa)).toMatchObject({ situacao: "interrompida" });
    expect(rastreio(resposta(conversa))).toEqual([VENDAS_ATRASOS]);
  });
});

describe("conversa lida do histórico", () => {
  const CONSULTA: ChamadaDoRastreio = {
    ferramenta: "vendas_atrasos",
    desfecho: "concluida",
    milissegundos: 182,
  };
  const NEGADA: ChamadaDoRastreio = {
    ferramenta: "exportar_tudo",
    desfecho: "nao_concluida",
    milissegundos: 3,
  };

  // Como a rota `GET /conversas/{id}` devolve: só os campos que o item tem.
  const LIDA: ConversaLida = {
    id: "conversa-1",
    titulo: "O que está causando os atrasos?",
    itens: [
      { autor: "usuario", texto: "O que está causando os atrasos?" },
      {
        autor: "assistente",
        texto: "Três rotas.",
        situacao: "concluida",
        id_da_pergunta: "pergunta-1",
        rastreio: [CONSULTA, NEGADA],
      },
      { autor: "usuario", texto: "E por lojista?" },
      {
        autor: "assistente",
        texto: "A Loja X ",
        situacao: "erro",
        erro: "O assistente está indisponível no momento.",
        id_da_pergunta: "pergunta-2",
        rastreio: [],
      },
      { autor: "usuario", texto: "E no mês?" },
      {
        autor: "assistente",
        texto: "",
        situacao: "interrompida",
        id_da_pergunta: "pergunta-3",
        rastreio: [],
      },
      { autor: "usuario", texto: "Todas as lojas?" },
      {
        autor: "assistente",
        texto: "Parte delas.",
        situacao: "concluida",
        aviso: "A resposta parou aqui.",
        id_da_pergunta: "pergunta-4",
        rastreio: [],
      },
    ],
  };

  it("mostra a conversa como estava: perguntas, respostas, situações, avisos, erros e rastreio", () => {
    const conversa = carregar(LIDA);

    expect(conversa.id).toBe("conversa-1");
    expect(conversa.perguntasERespostas).toEqual([
      { autor: "usuario", texto: "O que está causando os atrasos?" },
      {
        autor: "assistente",
        texto: "Três rotas.",
        situacao: "concluida",
        consultando: false,
        idDaPergunta: "pergunta-1",
        rastreio: [CONSULTA, NEGADA],
      },
      { autor: "usuario", texto: "E por lojista?" },
      {
        autor: "assistente",
        texto: "A Loja X ",
        situacao: "erro",
        consultando: false,
        erro: "O assistente está indisponível no momento.",
        idDaPergunta: "pergunta-2",
        rastreio: [],
      },
      { autor: "usuario", texto: "E no mês?" },
      {
        autor: "assistente",
        texto: "",
        situacao: "interrompida",
        consultando: false,
        idDaPergunta: "pergunta-3",
        rastreio: [],
      },
      { autor: "usuario", texto: "Todas as lojas?" },
      {
        autor: "assistente",
        texto: "Parte delas.",
        situacao: "concluida",
        consultando: false,
        aviso: "A resposta parou aqui.",
        idDaPergunta: "pergunta-4",
        rastreio: [],
      },
    ]);
    expect(respondendo(conversa)).toBe(false);
  });

  it("a pergunta seguinte continua a conversa carregada", () => {
    const conversa = enviar(carregar(LIDA), "E na semana?");

    expect(corpoDaPergunta(conversa, "E na semana?")).toEqual({
      pergunta: "E na semana?",
      id_da_conversa: "conversa-1",
    });
    expect(conversa.perguntasERespostas).toHaveLength(LIDA.itens.length + 2);
  });

  it("aceita a resposta da rota no contrato", () => {
    expect(eConversaLida(JSON.parse(JSON.stringify(LIDA)))).toBe(true);
    expect(eConversaLida({ id: "c", titulo: "Vazia", itens: [] })).toBe(true);
  });

  function comItem(item: unknown) {
    return { id: "c", titulo: "t", itens: [item] };
  }

  it.each([
    ["sem itens", { id: "c", titulo: "t" }],
    ["autor desconhecido", comItem({ autor: "sistema", texto: "x" })],
    ["resposta sem situação", comItem({ autor: "assistente", texto: "x", rastreio: [] })],
    [
      "situação de quem ainda responde",
      comItem({ autor: "assistente", texto: "x", situacao: "chegando", rastreio: [] }),
    ],
    [
      "chamada fora do contrato",
      comItem({
        autor: "assistente",
        texto: "x",
        situacao: "concluida",
        rastreio: [{ ferramenta: "x", desfecho: "negada", milissegundos: 1 }],
      }),
    ],
    ["nada", null],
  ])("recusa a resposta fora do contrato: %s", (_, valor) => {
    expect(eConversaLida(valor)).toBe(false);
  });
});

describe("conversa nova", () => {
  it("começa vazia e sem identificador: a próxima pergunta abre outra conversa na API", () => {
    const anterior = receber(enviar(CONVERSA_VAZIA, "Oi?"), {
      tipo: "conversa",
      idDaConversa: "conversa-1",
      idDaPergunta: "pergunta-1",
    });

    const nova = comecarNova();

    expect(anterior.id).toBe("conversa-1");
    expect(nova).toEqual(CONVERSA_VAZIA);
    expect(corpoDaPergunta(nova, "Outra coisa?")).toEqual({ pergunta: "Outra coisa?" });
  });
});
