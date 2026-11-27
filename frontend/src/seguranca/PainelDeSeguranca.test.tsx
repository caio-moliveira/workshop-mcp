import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { EstadoDoBloco } from "../useBloco";
import type { PainelDeSeguranca } from "./contrato";
import { cenario, execucao, PERMITIDO } from "./exemplos";
import { VisaoDoPainelDeSeguranca } from "./PainelDeSeguranca";

function html(estado: EstadoDoBloco<PainelDeSeguranca>): string {
  return renderToStaticMarkup(
    <VisaoDoPainelDeSeguranca estado={estado} tentarDeNovo={() => {}} />,
  );
}

function pronto(dados: PainelDeSeguranca): string {
  return html({ fase: "pronto", dados });
}

/** O HTML de cada cartão, pelo rótulo. */
function cartoes(marcacao: string): Record<string, string> {
  const porRotulo: Record<string, string> = {};
  for (const cartao of marcacao.split("<article").slice(1)) {
    const rotulo = /<h3[^>]*>([^<]+)<\/h3>/.exec(cartao)?.[1];
    if (rotulo) porRotulo[rotulo] = cartao;
  }
  return porRotulo;
}

/** As linhas da matriz, sem o cabeçalho. */
function linhas(marcacao: string): string[] {
  return marcacao.split("<tr").slice(1).filter((linha) => linha.includes("<td"));
}

const DIVERGENTE = cenario({
  id: "api-produtos-le-rota-do-comercial",
  descricao: "Produtos lê uma rota do Comercial e recebe o mesmo 403",
  quem: { tipo: "usuario", nome: "bruno.produtos" },
  perfil: "produtos",
  alvo: { tipo: "rota", nome: "/comercial/indicadores", parametros: {} },
  obtido: "permitido",
  divergencia: true,
  resposta: { status: 200, mensagem: null, linhas: 1 },
});

describe("painel de segurança com a última execução", () => {
  const marcacao = pronto({ execucao: execucao([PERMITIDO, cenario()]) });

  it("mostra os cartões de executados, permitidos, negados e divergências", () => {
    const porRotulo = cartoes(marcacao);
    expect(Object.keys(porRotulo)).toEqual([
      "Executados",
      "Permitidos",
      "Negados",
      "Divergências",
    ]);
    expect(porRotulo["Executados"]).toContain(">2<");
    expect(porRotulo["Permitidos"]).toContain(">1<");
    expect(porRotulo["Negados"]).toContain(">1<");
    expect(porRotulo["Divergências"]).toContain(">0<");
  });

  it("sem divergência, o cartão delas não fica em destaque", () => {
    expect(cartoes(marcacao)["Divergências"]).not.toContain('data-destaque="true"');
  });

  it("mostra a data e a hora da execução, em Brasília", () => {
    expect(marcacao).toContain("26/11/2026");
    expect(marcacao).toContain("11:03");
    expect(marcacao).toContain('dateTime="2026-11-26T14:03:12+00:00"');
  });

  it("a matriz tem as colunas Cenário, Perfil, Resultado e Detalhes", () => {
    const cabecalho = [...marcacao.matchAll(/<th scope="col"[^>]*>([^<]+)<\/th>/g)].map(
      (m) => m[1],
    );
    expect(cabecalho).toEqual(["Cenário", "Perfil", "Resultado", "Detalhes"]);
  });

  it("agrupa a matriz pela camada de defesa", () => {
    expect(marcacao).toMatch(/<th[^>]*scope="rowgroup"[^>]*>.*API/);
  });

  it("o permitido tem ícone e texto, e mostra só o status e as linhas", () => {
    const [permitido] = linhas(marcacao);
    expect(permitido).toContain("O dono lê a própria rota");
    expect(permitido).toContain("ana.vendas");
    expect(permitido).toMatch(/data-desfecho="permitido"[^>]*>.*<svg.*Permitido/);
    expect(permitido).toContain("200 · 10 linhas");
  });

  it("o negado tem ícone e texto, com a mensagem genérica", () => {
    const [, negado] = linhas(marcacao);
    expect(negado).toMatch(/data-desfecho="negado"[^>]*>.*<svg.*Negado/);
    expect(negado).toContain("403 · Acesso negado.");
  });

  it("sem divergência, nenhuma linha tem a marca", () => {
    expect(marcacao).not.toContain("Divergência:");
  });

  it("a matriz rola dentro do próprio contêiner, que recebe o foco do teclado", () => {
    expect(marcacao).toMatch(/role="region"[^>]*tabindex="0"/i);
  });

  it("não tem seletor de período", () => {
    expect(marcacao).not.toContain('aria-label="Período"');
  });
});

describe("painel de segurança com a lista de ferramentas", () => {
  it("o detalhe conta as ferramentas listadas, não linhas", () => {
    const lista = cenario({
      id: "lista-de-vendas",
      grupo: "lista_de_ferramentas",
      alvo: { tipo: "lista_de_ferramentas", nome: "tools/list", parametros: {} },
      camadas_de_defesa: ["lista_de_ferramentas"],
      esperado: "permitido",
      obtido: "permitido",
      resposta: { status: 200, mensagem: null, linhas: 5 },
    });
    const [linha] = linhas(pronto({ execucao: execucao([lista]) }));
    expect(linha).toContain("200 · 5 ferramentas");
  });
});

describe("painel de segurança com uma divergência", () => {
  const marcacao = pronto({ execucao: execucao([PERMITIDO, DIVERGENTE]) });

  it("o cartão das divergências fica em destaque", () => {
    const divergencias = cartoes(marcacao)["Divergências"];
    expect(divergencias).toContain('data-destaque="true"');
    expect(divergencias).toContain(">1<");
  });

  it("a linha divergente tem a marca, com o esperado", () => {
    const [, divergente] = linhas(marcacao);
    expect(divergente).toContain("Divergência: esperado negado");
    expect(linhas(marcacao)[0]).not.toContain("Divergência");
  });
});

describe("painel de segurança com os grupos Banco, Limite de frequência e Assistente", () => {
  const banco = cenario({
    id: "banco-vendas-le-a-camada-da-diretoria",
    descricao: "O papel vendas é recusado na camada da Diretoria",
    grupo: "banco",
    quem: { tipo: "papel", nome: "vendas" },
    alvo: { tipo: "camada_de_leitura", nome: "diretoria.indicadores", parametros: {} },
    camadas_de_defesa: ["banco"],
    resposta: {
      status: null,
      mensagem: "Recusado pelo banco: o papel não tem o privilégio (42501).",
      linhas: null,
    },
  });
  const limite = cenario({
    id: "limite-vitor-passa-do-limite",
    descricao: "vitor.vendas faz 31 chamadas seguidas e é barrado",
    grupo: "limite_de_frequencia",
    quem: { tipo: "usuario", nome: "vitor.vendas" },
    alvo: { tipo: "ferramenta", nome: "vendas_indicadores", parametros: { periodo: "30d" } },
    camadas_de_defesa: ["limite_de_frequencia"],
    resposta: {
      status: null,
      mensagem: "Muitas chamadas em pouco tempo. Tente de novo em instantes.",
      linhas: null,
    },
  });
  const assistente = cenario({
    id: "assistente-ferramenta-de-outro-perfil",
    descricao: "O modelo tenta uma ferramenta de outro perfil: não listada e recusada",
    grupo: "assistente",
    quem: { tipo: "usuario", nome: "bruno.produtos" },
    perfil: "produtos",
    alvo: { tipo: "assistente", nome: "/assistente", parametros: {} },
    camadas_de_defesa: ["lista_de_ferramentas", "chamada"],
  });
  const marcacao = pronto({ execucao: execucao([assistente, limite, banco]) });

  it("mostra os três grupos, na ordem das camadas de defesa", () => {
    const grupos = [...marcacao.matchAll(/<th[^>]*scope="rowgroup"[^>]*>([^<]+)<\/th>/g)].map(
      (m) => m[1],
    );
    expect(grupos).toEqual(["Banco", "Limite de frequência", "Assistente"]);
  });

  it("um cenário do banco mostra o papel e a recusa, sem status HTTP", () => {
    const [linhaDoBanco] = linhas(marcacao);
    expect(linhaDoBanco).toContain("vendas");
    expect(linhaDoBanco).toContain(">Recusado pelo banco: o papel não tem o privilégio (42501).<");
  });

  it("o limite mostra a mensagem genérica da barreira", () => {
    expect(linhas(marcacao)[1]).toContain("Muitas chamadas em pouco tempo.");
  });
});

describe("painel de segurança com a conferência da carga", () => {
  it("diz quando o banco está no estado da carga", () => {
    const carga = { confere: true, data_de_referencia: "2026-11-30", detalhe: null };
    const marcacao = pronto({ execucao: { ...execucao(), carga } });
    expect(marcacao).toContain("O banco está no estado da carga.");
  });

  it("avisa quando não está, com o que difere", () => {
    const carga = {
      confere: false,
      data_de_referencia: "2026-11-30",
      detalhe: "pedido com 100 linhas, esperadas 29999",
    };
    const marcacao = pronto({ execucao: { ...execucao(), carga } });
    expect(marcacao).toContain(
      "O banco não está no estado da carga: pedido com 100 linhas, esperadas 29999",
    );
  });
});

describe("cartões da matriz completa", () => {
  const MATRIZ = {
    executada_em: "2026-11-26T14:03:40+00:00",
    pares: 140,
    permitidos: 35,
    negados: 105,
    divergencias: 0,
  };

  function comMatriz(alteracoes: Partial<typeof MATRIZ> = {}): string {
    return pronto({ execucao: { ...execucao(), matriz_completa: { ...MATRIZ, ...alteracoes } } });
  }

  it("mostram os pares executados, os permitidos, os negados e as divergências", () => {
    const porRotulo = cartoes(comMatriz());
    expect(porRotulo["Pares executados"]).toContain(">140<");
    expect(porRotulo["Pares permitidos"]).toContain(">35<");
    expect(porRotulo["Pares negados"]).toContain(">105<");
    expect(porRotulo["Divergências na matriz"]).toContain(">0<");
    expect(porRotulo["Divergências na matriz"]).not.toContain('data-destaque="true"');
  });

  it("mostram a data própria da matriz", () => {
    expect(comMatriz()).toContain('dateTime="2026-11-26T14:03:40+00:00"');
  });

  it("com divergência na matriz, o cartão dela fica em destaque", () => {
    const porRotulo = cartoes(comMatriz({ permitidos: 36, divergencias: 1 }));
    expect(porRotulo["Divergências na matriz"]).toContain(">1<");
    expect(porRotulo["Divergências na matriz"]).toContain('data-destaque="true"');
  });

  it("sem a matriz gravada, os cartões dela não aparecem", () => {
    expect(Object.keys(cartoes(pronto({ execucao: execucao() })))).not.toContain(
      "Pares executados",
    );
  });
});

describe("estados do painel de segurança", () => {
  it("sem execução gravada, mostra o estado vazio com o comando a rodar", () => {
    const marcacao = pronto({ execucao: null });
    expect(marcacao).toContain("Nenhuma execução de aceite");
    expect(marcacao).toContain("uv run python tests/execucao_de_aceite.py");
    expect(marcacao).not.toContain("<table");
  });

  it("enquanto carrega, anuncia o carregamento", () => {
    const marcacao = html({ fase: "carregando" });
    expect(marcacao).toMatch(/role="status"[^>]*>.*Carregando a execução de aceite…/);
    expect(marcacao).not.toContain("<table");
  });

  it("na falha, mostra o erro com a opção de tentar de novo", () => {
    const marcacao = html({ fase: "erro" });
    expect(marcacao).toContain("a execução de aceite");
    expect(marcacao).toContain("Tentar de novo");
  });

  it("o cabeçalho é o mesmo em todos os estados", () => {
    for (const estado of [{ fase: "carregando" }, { fase: "erro" }] as const) {
      expect(html(estado)).toContain(">Segurança</h1>");
    }
  });
});
