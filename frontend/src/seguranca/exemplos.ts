/** Exemplos do contrato do painel de segurança, para os testes. */
import type { CenarioExecutado, ExecucaoDeAceite } from "./contrato";

export function cenario(alteracoes: Partial<CenarioExecutado> = {}): CenarioExecutado {
  return {
    id: "api-vendas-le-rota-da-diretoria",
    descricao: "Vendas lê uma rota da Diretoria",
    grupo: "api",
    quem: { tipo: "usuario", nome: "ana.vendas" },
    perfil: "vendas",
    alvo: { tipo: "rota", nome: "/diretoria/indicadores", parametros: {} },
    camadas_de_defesa: ["api"],
    esperado: "negado",
    obtido: "negado",
    divergencia: false,
    resposta: { status: 403, mensagem: "Acesso negado.", linhas: null },
    auditoria: null,
    duracao_em_ms: 4,
    ...alteracoes,
  };
}

export const PERMITIDO = cenario({
  id: "api-dono-le-a-propria-rota",
  descricao: "O dono lê a própria rota",
  alvo: { tipo: "rota", nome: "/vendas/pedidos-recentes", parametros: {} },
  esperado: "permitido",
  obtido: "permitido",
  resposta: { status: 200, mensagem: null, linhas: 10 },
  duracao_em_ms: 30,
});

/** Uma execução com o resumo contado dos cenários dados. */
export function execucao(cenarios: CenarioExecutado[] = [cenario()]): ExecucaoDeAceite {
  return {
    executada_em: "2026-11-26T14:03:12+00:00",
    resumo: {
      executados: cenarios.length,
      permitidos: cenarios.filter((c) => c.obtido === "permitido").length,
      negados: cenarios.filter((c) => c.obtido === "negado").length,
      divergencias: cenarios.filter((c) => c.divergencia).length,
    },
    matriz_completa: null,
    carga: null,
    cenarios,
  };
}
