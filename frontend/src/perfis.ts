import type { CSSProperties } from "react";

/** Os quatro perfis, com o identificador que a API devolve em `GET /eu` (claim `perfil`). */
export const PERFIS = ["vendas", "produtos", "comercial", "diretoria"] as const;

export type Perfil = (typeof PERFIS)[number];

interface DescricaoDoPerfil {
  /** Nome de exibição do perfil. */
  nome: string;
  /** Cor de identificação do perfil (FE §2), como propriedade customizada. */
  cor: string;
  /** Rótulo do painel do perfil, na sidebar e no cabeçalho. */
  rotuloDoPainel: string;
  /** A pergunta sugerida no painel do assistente (FE §6); só os perfis com ferramentas têm uma. */
  perguntaSugerida?: string;
}

export const DESCRICAO_DOS_PERFIS: Record<Perfil, DescricaoDoPerfil> = {
  vendas: {
    nome: "Vendas",
    cor: "var(--perfil-vendas)",
    rotuloDoPainel: "Painel de Vendas",
    perguntaSugerida: "O que está causando os atrasos?",
  },
  produtos: {
    nome: "Produtos",
    cor: "var(--perfil-produtos)",
    rotuloDoPainel: "Painel de Produtos",
    perguntaSugerida: "Quais categorias concentram as piores notas?",
  },
  comercial: {
    nome: "Comercial",
    cor: "var(--perfil-comercial)",
    rotuloDoPainel: "Painel Comercial",
    perguntaSugerida: "Qual canal traz os leads que mais convertem?",
  },
  diretoria: {
    nome: "Diretoria",
    cor: "var(--perfil-diretoria)",
    rotuloDoPainel: "Painel da Diretoria",
  },
};

export function ePerfil(valor: unknown): valor is Perfil {
  return typeof valor === "string" && (PERFIS as readonly string[]).includes(valor);
}

/**
 * Põe a cor do perfil em `--cor-do-perfil` no elemento. O CSS de cada componente decide onde ela
 * aparece: só em ícone, linha curta ou chip (FE §2).
 */
export function corDoPerfil(perfil: Perfil): CSSProperties {
  return { "--cor-do-perfil": DESCRICAO_DOS_PERFIS[perfil].cor } as CSSProperties;
}
