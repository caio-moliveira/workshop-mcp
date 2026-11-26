import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { Perfil } from "../perfis";
import type { Conversa } from "./conversa";
import { PainelDoAssistente } from "./PainelDoAssistente";
import type { FonteDoAssistente } from "./useConversa";

// O desenho inicial do painel, sem efeitos: o que cada modo põe na tela antes de qualquer clique.
// O visual (larguras, colunas, animação) é conferido no roteiro manual da 5b.

const FONTE: FonteDoAssistente = {
  // eslint-disable-next-line require-yield
  async *perguntar() {
    return;
  },
  listarConversas: () => new Promise(() => {}),
  lerConversa: () => new Promise(() => {}),
  apagarConversa: () => Promise.resolve(),
};

const CONVERSA: Conversa = {
  id: "conversa-1",
  perguntasERespostas: [
    { autor: "usuario", texto: "Quais rotas atrasam mais?" },
    {
      autor: "assistente",
      texto: "A rota **SP → RJ** atrasa mais.",
      situacao: "concluida",
      consultando: false,
      idDaPergunta: "pergunta-1",
      rastreio: [{ ferramenta: "atrasos_por_rota", desfecho: "concluida", milissegundos: 42 }],
    },
  ],
};

const SEM_ACAO = () => {};

function desenhar(
  modo: { expandido: boolean; podeExpandir: boolean },
  conversa = CONVERSA,
  usuario: { nome: string; perfil: Perfil } = { nome: "Ana", perfil: "vendas" },
) {
  return renderToStaticMarkup(
    <PainelDoAssistente
      usuario={usuario}
      fonte={FONTE}
      conversa={conversa}
      abertura={{ situacao: "pronta" }}
      expandido={modo.expandido}
      aoAlternarExpansao={modo.podeExpandir ? SEM_ACAO : undefined}
      aoPerguntar={SEM_ACAO}
      aoParar={SEM_ACAO}
      aoAbrir={SEM_ACAO}
      aoComecarNova={SEM_ACAO}
      aoFechar={SEM_ACAO}
      aoTerminarResposta={() => SEM_ACAO}
    />,
  );
}

describe("painel do assistente", () => {
  it("no painel lateral, oferece expandir e o botão Conversas", () => {
    const html = desenhar({ expandido: false, podeExpandir: true });

    expect(html).toContain('aria-label="Expandir o assistente"');
    expect(html).toContain('aria-label="Conversas"');
  });

  it("em tela pequena, não há botão de expandir, e o botão Conversas continua", () => {
    const html = desenhar({ expandido: false, podeExpandir: false });

    expect(html).not.toContain("Expandir o assistente");
    expect(html).toContain('aria-label="Conversas"');
  });

  it("expandido, mostra a lista de conversas ao lado da conversa, que segue na tela", () => {
    const html = desenhar({ expandido: true, podeExpandir: true });

    expect(html).toContain('aria-label="Recolher o assistente"');
    expect(html).toContain("Carregando as conversas…");
    expect(html).toContain("Quais rotas atrasam mais?");
    expect(html).toContain("<strong>SP → RJ</strong>");
    // Com a lista sempre ao lado, o botão que troca a conversa pela lista sai.
    expect(html).not.toContain('aria-label="Conversas"');
  });

  it("expandido, cada resposta terminada mantém o bloco do rastreio", () => {
    const html = desenhar({ expandido: true, podeExpandir: true });

    expect(html).toContain("Como esta resposta foi obtida");
  });

  it("expandido e vazio, a pergunta sugerida vem numa linha, com o campo da pergunta", () => {
    const html = desenhar({ expandido: true, podeExpandir: true }, { perguntasERespostas: [] });

    expect(html).toMatch(/<ul[^>]*aria-label="Sugestões"/);
    expect(html).toContain('id="pergunta-ao-assistente"');
  });

  it("vazio, o assistente de Produtos sugere a pergunta das categorias de piores notas", () => {
    const html = desenhar({ expandido: false, podeExpandir: true }, { perguntasERespostas: [] }, {
      nome: "Bruno",
      perfil: "produtos",
    });

    expect(html).toContain("Quais categorias concentram as piores notas?");
  });

  it("uma resposta chegando mostra o indicador discreto com o texto de estado", () => {
    const chegando: Conversa = {
      perguntasERespostas: [
        { autor: "usuario", texto: "Quais rotas atrasam mais?" },
        { autor: "assistente", texto: "", situacao: "chegando", consultando: true, rastreio: [] },
      ],
    };

    const html = desenhar({ expandido: true, podeExpandir: true }, chegando);

    expect(html).toContain("Consultando os dados…");
    expect(html).not.toContain("Como esta resposta foi obtida");
  });

  it("antes do primeiro trecho e sem consulta, o estado diz que a resposta está a caminho", () => {
    const comecando: Conversa = {
      perguntasERespostas: [
        { autor: "usuario", texto: "Oi" },
        { autor: "assistente", texto: "", situacao: "chegando", consultando: false, rastreio: [] },
      ],
    };

    const html = desenhar({ expandido: false, podeExpandir: true }, comecando);

    expect(html).toContain("Preparando a resposta…");
  });
});
