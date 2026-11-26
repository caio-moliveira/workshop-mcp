import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { CenarioDeSeguranca } from "./contrato";
import { cenario, execucao, PERMITIDO } from "./exemplos";
import { GavetaDoCenario } from "./GavetaDoCenario";
import { VisaoDoPainelDeSeguranca } from "./PainelDeSeguranca";

const DE_OUTRO_PERFIL = cenario({
  id: "chamada-vendas-chama-ferramenta-da-diretoria",
  descricao: "Vendas chama uma ferramenta da Diretoria: não listada e recusada",
  grupo: "chamada",
  alvo: {
    tipo: "ferramenta",
    nome: "diretoria_resumo",
    parametros: { periodo: "12m" },
  },
  camadas_de_defesa: ["lista_de_ferramentas", "chamada"],
  resposta: { status: 200, mensagem: "Ferramenta desconhecida.", linhas: null },
  auditoria: {
    id: 624,
    horario: "2026-11-26T21:23:22.448862+00:00",
    usuario: "Ana Ribeiro",
    ferramenta: "diretoria_resumo",
    argumentos: { periodo: "12m" },
    resultado: "negada",
  },
  duracao_em_ms: 16,
});

function gaveta(escolhido: CenarioDeSeguranca): string {
  return renderToStaticMarkup(<GavetaDoCenario cenario={escolhido} aoFechar={() => {}} />);
}

/** O texto da marcação, sem as tags, para conferir o que a gaveta diz. */
function texto(marcacao: string): string {
  return marcacao.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
}

describe("gaveta lateral de um cenário", () => {
  const marcacao = gaveta(DE_OUTRO_PERFIL);

  it("é um diálogo com o rótulo acessível do cenário", () => {
    const id = /aria-labelledby="([^"]+)"/.exec(marcacao)?.[1];
    expect(marcacao).toMatch(/<aside[^>]*role="dialog"/);
    expect(id).toBeTruthy();
    expect(marcacao).toMatch(
      new RegExp(`id="${id}"[^>]*>Vendas chama uma ferramenta da Diretoria`),
    );
  });

  it("recebe o foco ao abrir e tem um botão de fechar que anuncia o Esc", () => {
    expect(marcacao).toMatch(/<aside[^>]*tabindex="-1"/i);
    expect(marcacao).toMatch(/<button[^>]*aria-label="Fechar o detalhe do cenário"/);
    expect(marcacao).toContain('aria-keyshortcuts="Escape"');
  });

  it("mostra o pedido: quem, o quê e com quais parâmetros", () => {
    const dito = texto(marcacao);
    expect(dito).toContain("ana.vendas");
    expect(dito).toContain("Vendas");
    expect(dito).toContain("diretoria_resumo");
    expect(dito).toContain("periodo = 12m");
  });

  it("mostra a resposta com o status e a mensagem genérica da negação", () => {
    const dito = texto(marcacao);
    expect(dito).toContain("Negado");
    expect(dito).toContain("200");
    expect(dito).toContain("Ferramenta desconhecida.");
  });

  it("mostra as duas camadas de defesa que barraram", () => {
    const camadas = /aria-label="Camadas de defesa"[^>]*>(.*?)<\/ul>/.exec(marcacao)?.[1] ?? "";
    expect(texto(camadas).trim()).toBe("Lista de ferramentas Chamada");
    expect(texto(marcacao)).toContain("Barrado por");
  });

  it("mostra a linha da auditoria, com o usuário, a ferramenta e o desfecho", () => {
    const dito = texto(marcacao);
    expect(dito).toContain("Auditoria");
    expect(dito).toContain("Ana Ribeiro");
    expect(dito).toContain("negada");
    expect(dito).toContain("#624");
    expect(marcacao).toContain('dateTime="2026-11-26T21:23:22.448862+00:00"');
  });

  it("mostra a duração", () => {
    expect(texto(marcacao)).toContain("16 ms");
  });

  it("não mostra token", () => {
    expect(marcacao).not.toContain("eyJ");
  });
});

describe("gaveta de um cenário permitido e sem chamada", () => {
  const marcacao = texto(gaveta(PERMITIDO));

  it("mostra só o status e a quantidade de linhas", () => {
    expect(marcacao).toContain("Permitido");
    expect(marcacao).toContain("200");
    expect(marcacao).toContain("10 linhas");
  });

  it("diz que nenhuma camada barrou e que não há linha da auditoria", () => {
    expect(marcacao).toContain("Nenhuma camada barrou");
    expect(marcacao).toContain("Sem linha na auditoria");
  });
});

describe("gaveta do cenário negado do assistente", () => {
  const marcacao = texto(
    gaveta(
      cenario({
        id: "assistente-ferramenta-de-outro-perfil",
        grupo: "assistente",
        alvo: {
          tipo: "assistente",
          nome: "/assistente",
          parametros: { ferramenta: "comercial_indicadores", periodo: "30d" },
        },
        camadas_de_defesa: ["lista_de_ferramentas", "chamada"],
        resposta: { status: 200, mensagem: "Ferramenta desconhecida.", linhas: null },
      }),
    ),
  );

  it("explica que a recusa aconteceu no assistente, antes de chegar ao servidor MCP", () => {
    expect(marcacao).toContain(
      "Sem linha na auditoria: a recusa aconteceu no assistente, antes de chegar ao servidor MCP, por isso não há chamada registrada.",
    );
    expect(marcacao).not.toContain("só as chamadas de ferramenta");
  });
});

describe("gaveta de um cenário da lista de ferramentas", () => {
  it("conta as ferramentas listadas, não linhas", () => {
    const lista = cenario({
      id: "lista-de-vendas",
      grupo: "lista_de_ferramentas",
      alvo: { tipo: "lista_de_ferramentas", nome: "tools/list", parametros: {} },
      camadas_de_defesa: ["lista_de_ferramentas"],
      esperado: "permitido",
      obtido: "permitido",
      resposta: { status: 200, mensagem: null, linhas: 5 },
    });
    const marcacao = texto(gaveta(lista));
    expect(marcacao).toContain("5 ferramentas");
    expect(marcacao).not.toContain("5 linhas");
  });
});

describe("gaveta de um cenário divergente", () => {
  it("mostra o esperado ao lado do obtido", () => {
    const divergente = cenario({
      obtido: "permitido",
      divergencia: true,
      resposta: { status: 200, mensagem: null, linhas: 1 },
    });
    expect(texto(gaveta(divergente))).toContain("Divergência: esperado negado");
  });
});

describe("linhas da matriz", () => {
  const marcacao = renderToStaticMarkup(
    <VisaoDoPainelDeSeguranca
      estado={{
        fase: "pronto",
        dados: { execucao: execucao([PERMITIDO, DE_OUTRO_PERFIL]) },
      }}
      tentarDeNovo={() => {}}
    />,
  );

  it("cada linha abre a gaveta por um botão, alcançável pelo teclado", () => {
    const botoes = [...marcacao.matchAll(/<button[^>]*aria-haspopup="dialog"[^>]*>/g)];
    expect(botoes).toHaveLength(2);
    for (const [botao] of botoes) {
      expect(botao).toContain('aria-expanded="false"');
      expect(botao).toContain('type="button"');
    }
  });

  it("sem cenário escolhido, a gaveta não aparece", () => {
    expect(marcacao).not.toContain('role="dialog"');
  });
});
