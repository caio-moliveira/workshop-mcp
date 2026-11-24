/**
 * O que muda de um ambiente para outro. Não entra no build: o navegador busca em
 * `/configuracao.json`, servido pelo nginx no compose e pelo Vite em desenvolvimento.
 */
export interface Configuracao {
  /** Endereço público do provedor de identidade, o mesmo de ENDERECO_PUBLICO_DO_PROVEDOR. */
  enderecoDoProvedor: string;
  /** Endereço da API como o navegador a alcança. */
  enderecoDaApi: string;
  /** Inatividade que encerra a sessão, a mesma do realm (INATIVIDADE_DA_SESSAO_EM_SEGUNDOS). */
  inatividadeDaSessaoEmSegundos: number;
}

function eConfiguracao(valor: unknown): valor is Configuracao {
  if (typeof valor !== "object" || valor === null) return false;
  const { enderecoDoProvedor, enderecoDaApi, inatividadeDaSessaoEmSegundos } = valor as Record<
    string,
    unknown
  >;
  return (
    typeof enderecoDoProvedor === "string" &&
    typeof enderecoDaApi === "string" &&
    typeof inatividadeDaSessaoEmSegundos === "number" &&
    inatividadeDaSessaoEmSegundos > 0
  );
}

export async function carregarConfiguracao(): Promise<Configuracao> {
  const resposta = await fetch("/configuracao.json", { cache: "no-store" });
  if (!resposta.ok) throw new Error(`configuracao.json respondeu ${resposta.status}`);
  const valor: unknown = await resposta.json();
  if (!eConfiguracao(valor)) throw new Error("configuracao.json incompleto");
  return valor;
}
