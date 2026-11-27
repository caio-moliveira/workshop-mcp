/** Os textos do painel de segurança comuns à matriz e à gaveta lateral. */
import { formatarNumero } from "../formatacao";
import { DESCRICAO_DOS_PERFIS, type Perfil } from "../perfis";
import type { CenarioDeSeguranca } from "./contrato";

/** O que aparece no lugar do perfil quando quem pede não tem um: um token, sem usuário. */
export const SEM_PERFIL = "Sem perfil";

export function nomeDoPerfil(perfil: Perfil | null): string {
  return perfil ? DESCRICAO_DOS_PERFIS[perfil].nome : SEM_PERFIL;
}

/** O que a quantidade de um permitido conta: as ferramentas listadas ou as linhas da resposta. */
export function unidadeDaQuantidade({ alvo }: CenarioDeSeguranca): "Ferramentas" | "Linhas" {
  return alvo.tipo === "lista_de_ferramentas" ? "Ferramentas" : "Linhas";
}

/** A quantidade de um permitido por extenso: "1 linha", "10 linhas", "5 ferramentas". */
export function quantidadePorExtenso(cenario: CenarioDeSeguranca, quantidade: number): string {
  const ferramentas = unidadeDaQuantidade(cenario) === "Ferramentas";
  if (quantidade === 1) return ferramentas ? "1 ferramenta" : "1 linha";
  return `${formatarNumero(quantidade)} ${ferramentas ? "ferramentas" : "linhas"}`;
}
