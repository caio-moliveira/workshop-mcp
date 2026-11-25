import { describe, expect, it } from "vitest";

import { lerEventos, RESPOSTA_INTERROMPIDA, type EventoDaResposta } from "./fluxo";

const codificador = new TextEncoder();

async function* pedacos(...textos: (string | Uint8Array)[]): AsyncGenerator<Uint8Array> {
  for (const texto of textos) yield typeof texto === "string" ? codificador.encode(texto) : texto;
}

async function todos(fluxo: AsyncIterable<EventoDaResposta>): Promise<EventoDaResposta[]> {
  const eventos: EventoDaResposta[] = [];
  for await (const evento of fluxo) eventos.push(evento);
  return eventos;
}

describe("lerEventos", () => {
  it("lê um evento inteiro num pedaço", async () => {
    const eventos = await todos(
      lerEventos(
        pedacos('event: texto\ndata: {"texto": "Os atrasos"}\n\n', "event: fim\ndata: {}\n\n"),
      ),
    );
    expect(eventos).toEqual([{ tipo: "texto", texto: "Os atrasos" }, { tipo: "fim" }]);
  });

  it("junta um evento partido entre pedaços, inclusive no meio de um caractere", async () => {
    const bytes = codificador.encode('event: texto\ndata: {"texto": "concentração"}\n\n');
    const meioDoCa = bytes.indexOf(0xc3) + 1; // entre os dois bytes do "ç"
    const eventos = await todos(
      lerEventos(
        pedacos(
          "eve",
          bytes.slice(3, meioDoCa),
          bytes.slice(meioDoCa),
          "event: fim\n",
          "data: {}\n\n",
        ),
      ),
    );
    expect(eventos).toEqual([{ tipo: "texto", texto: "concentração" }, { tipo: "fim" }]);
  });

  it("lê vários eventos num pedaço só, ignorando comentários de manutenção", async () => {
    const eventos = await todos(
      lerEventos(
        pedacos(
          ": ping\n\n" +
            'event: estado\ndata: {"estado": "consultando"}\n\n' +
            'event: texto\ndata: {"texto": "Três "}\n\n' +
            'event: texto\ndata: {"texto": "lojistas"}\n\n' +
            "event: fim\ndata: {}\n\n",
        ),
      ),
    );
    expect(eventos).toEqual([
      { tipo: "estado" },
      { tipo: "texto", texto: "Três " },
      { tipo: "texto", texto: "lojistas" },
      { tipo: "fim" },
    ]);
  });

  it("aceita linhas terminadas em CRLF", async () => {
    const eventos = await todos(
      lerEventos(
        pedacos('event: texto\r\ndata: {"texto": "a"}\r\n\r\nevent: fim\r\ndata: {}\r\n\r\n'),
      ),
    );
    expect(eventos).toEqual([{ tipo: "texto", texto: "a" }, { tipo: "fim" }]);
  });

  it("entrega o aviso que vem no fim", async () => {
    const aviso = "Aviso do fim, escrito pela API.";
    const eventos = await todos(
      lerEventos(
        pedacos(
          'event: texto\ndata: {"texto": "Parcial"}\n\n',
          `event: fim\ndata: ${JSON.stringify({ aviso })}\n\n`,
        ),
      ),
    );
    expect(eventos).toEqual([
      { tipo: "texto", texto: "Parcial" },
      { tipo: "fim", aviso },
    ]);
  });

  it("entrega o erro com a mensagem do servidor e para ali", async () => {
    const mensagem = "Mensagem de erro, escrita pela API.";
    const eventos = await todos(
      lerEventos(
        pedacos(
          'event: texto\ndata: {"texto": "Parcial"}\n\n',
          `event: erro\ndata: ${JSON.stringify({ erro: mensagem })}\n\n`,
          'event: texto\ndata: {"texto": "depois do erro"}\n\n',
        ),
      ),
    );
    expect(eventos).toEqual([
      { tipo: "texto", texto: "Parcial" },
      { tipo: "erro", mensagem },
    ]);
  });

  it("termina em erro quando o fluxo acaba sem fim", async () => {
    const eventos = await todos(
      lerEventos(
        pedacos('event: texto\ndata: {"texto": "Os atrasos"}\n\n', 'event: texto\ndata: {"tex'),
      ),
    );
    expect(eventos).toEqual([
      { tipo: "texto", texto: "Os atrasos" },
      { tipo: "erro", mensagem: RESPOSTA_INTERROMPIDA },
    ]);
  });

  it("entrega a conversa e a pergunta do primeiro evento", async () => {
    const eventos = await todos(
      lerEventos(
        pedacos(
          'event: conversa\ndata: {"id_da_conversa": "c-1", "id_da_pergunta": "p-1"}\n\n',
          'event: texto\ndata: {"texto": "Oi"}\n\n',
          "event: fim\ndata: {}\n\n",
        ),
      ),
    );
    expect(eventos).toEqual([
      { tipo: "conversa", idDaConversa: "c-1", idDaPergunta: "p-1" },
      { tipo: "texto", texto: "Oi" },
      { tipo: "fim" },
    ]);
  });

  it("termina em erro quando o evento da conversa vem sem os identificadores", async () => {
    const eventos = await todos(
      lerEventos(pedacos('event: conversa\ndata: {"id_da_conversa": "c-1"}\n\n')),
    );
    expect(eventos).toEqual([{ tipo: "erro", mensagem: RESPOSTA_INTERROMPIDA }]);
  });

  it("termina em erro quando um evento traz dados fora do contrato", async () => {
    const eventos = await todos(
      lerEventos(pedacos("event: texto\ndata: não é JSON\n\n", "event: fim\ndata: {}\n\n")),
    );
    expect(eventos).toEqual([{ tipo: "erro", mensagem: RESPOSTA_INTERROMPIDA }]);
  });
});
