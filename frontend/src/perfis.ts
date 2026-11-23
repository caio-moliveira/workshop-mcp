/** Os quatro perfis, com o identificador que a API devolve em `GET /eu` (claim `perfil`). */
export const PERFIS = ["vendas", "produtos", "comercial", "diretoria"] as const;

export type Perfil = (typeof PERFIS)[number];

interface DescricaoDoPerfil {
  /** Nome de exibição do perfil. */
  nome: string;
  /** Cor de identificação do perfil (FE §2), como propriedade customizada. */
  cor: string;
  /** Rótulo do item da área do perfil na sidebar. */
  area: string;
}

export const DESCRICAO_DOS_PERFIS: Record<Perfil, DescricaoDoPerfil> = {
  vendas: { nome: "Vendas", cor: "var(--perfil-vendas)", area: "Painel de Vendas" },
  produtos: { nome: "Produtos", cor: "var(--perfil-produtos)", area: "Painel de Produtos" },
  comercial: { nome: "Comercial", cor: "var(--perfil-comercial)", area: "Painel Comercial" },
  diretoria: { nome: "Diretoria", cor: "var(--perfil-diretoria)", area: "Painel da Diretoria" },
};

export function ePerfil(valor: unknown): valor is Perfil {
  return typeof valor === "string" && (PERFIS as readonly string[]).includes(valor);
}
