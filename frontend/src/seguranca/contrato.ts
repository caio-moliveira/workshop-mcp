/**
 * O contrato de `GET /seguranca`: a última execução de aceite, como o backend a grava
 * (backend/aceite/resultado.py). A resposta chega como `unknown` e só é usada depois de validada.
 */
import { eContagem, eDataIso, eObjeto, eTexto, eUmDe } from "../painel/contrato";
import { ePerfil, type Perfil } from "../perfis";

/** Os pontos que podem barrar um pedido, na ordem em que um pedido os atravessa (glossário). */
export const CAMADAS_DE_DEFESA = [
  "token",
  "lista_de_ferramentas",
  "chamada",
  "api",
  "banco",
  "limite_de_frequencia",
] as const;
export type CamadaDeDefesa = (typeof CAMADAS_DE_DEFESA)[number];

/** Os grupos da matriz: um por camada de defesa e o do assistente, barrado na Chamada. */
export const GRUPOS = [...CAMADAS_DE_DEFESA, "assistente"] as const;
export type Grupo = (typeof GRUPOS)[number];

/** O rótulo de cada grupo da matriz; o de uma camada de defesa é o do grupo dela. */
export const ROTULO_DO_GRUPO: Record<Grupo, string> = {
  token: "Token",
  lista_de_ferramentas: "Lista de ferramentas",
  chamada: "Chamada",
  api: "API",
  banco: "Banco",
  limite_de_frequencia: "Limite de frequência",
  assistente: "Assistente",
};

export const DESFECHOS = ["permitido", "negado"] as const;
export type Desfecho = (typeof DESFECHOS)[number];

const TIPOS_DE_QUEM = ["usuario", "papel", "token"] as const;
const TIPOS_DE_ALVO = [
  "rota",
  "ferramenta",
  "lista_de_ferramentas",
  "camada_de_leitura",
  "dados_de_origem",
  "conversa",
  "assistente",
] as const;

/** Quantos foram permitidos, quantos negados e quantos divergiram do esperado. */
export interface ContagemDeDesfechos {
  permitidos: number;
  negados: number;
  divergencias: number;
}

export interface Contagem extends ContagemDeDesfechos {
  executados: number;
}

export interface MatrizCompleta extends ContagemDeDesfechos {
  executada_em: string;
  pares: number;
}

export interface ConferenciaDaCarga {
  confere: boolean;
  data_de_referencia: string | null;
  detalhe: string | null;
}

export interface Quem {
  tipo: (typeof TIPOS_DE_QUEM)[number];
  nome: string;
}

export interface Alvo {
  tipo: (typeof TIPOS_DE_ALVO)[number];
  nome: string;
  parametros: Record<string, string | number>;
}

/** No permitido, só o status e a quantidade de linhas; a mensagem é só da negação. */
export interface Resposta {
  status: number | null;
  mensagem: string | null;
  linhas: number | null;
}

export interface LinhaDaAuditoria {
  id: number;
  horario: string;
  usuario: string;
  ferramenta: string;
  argumentos: Record<string, unknown> | null;
  resultado: string;
}

export interface CenarioDeSeguranca {
  id: string;
  descricao: string;
  grupo: Grupo;
  quem: Quem;
  perfil: Perfil | null;
  alvo: Alvo;
  camadas_de_defesa: CamadaDeDefesa[];
  esperado: Desfecho;
  obtido: Desfecho;
  divergencia: boolean;
  resposta: Resposta;
  auditoria: LinhaDaAuditoria | null;
  duracao_em_ms: number;
}

export interface ExecucaoDeAceite {
  executada_em: string;
  resumo: Contagem;
  matriz_completa: MatrizCompleta | null;
  carga: ConferenciaDaCarga | null;
  cenarios: CenarioDeSeguranca[];
}

/** A resposta da rota: `execucao` é `null` enquanto nenhuma execução foi gravada. */
export interface PainelDeSeguranca {
  execucao: ExecucaoDeAceite | null;
}

/** Um instante ISO com hora ("2026-11-26T14:03:12+00:00"). */
export function eInstante(valor: unknown): valor is string {
  return (
    typeof valor === "string" &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(valor) &&
    !Number.isNaN(Date.parse(valor))
  );
}

function eTextoOuNulo(valor: unknown): valor is string | null {
  return valor === null || typeof valor === "string";
}

function eContagemOuNula(valor: unknown): valor is number | null {
  return valor === null || eContagem(valor);
}

/**
 * Uma contagem de permitidos, negados e divergências sobre `total`: cada um é permitido ou
 * negado, e só diverge o que foi contado.
 */
function eContagemDeDesfechos(valor: Record<string, unknown>, total: unknown): total is number {
  const { permitidos, negados, divergencias } = valor;
  return (
    eContagem(total) &&
    eContagem(permitidos) &&
    eContagem(negados) &&
    eContagem(divergencias) &&
    permitidos + negados === total &&
    divergencias <= total
  );
}

export function eContagemDoResumo(valor: unknown): valor is Contagem {
  return eObjeto(valor) && eContagemDeDesfechos(valor, valor.executados);
}

export function eMatrizCompleta(valor: unknown): valor is MatrizCompleta {
  return (
    eObjeto(valor) && eInstante(valor.executada_em) && eContagemDeDesfechos(valor, valor.pares)
  );
}

export function eConferenciaDaCarga(valor: unknown): valor is ConferenciaDaCarga {
  if (!eObjeto(valor)) return false;
  return (
    typeof valor.confere === "boolean" &&
    (valor.data_de_referencia === null || eDataIso(valor.data_de_referencia)) &&
    eTextoOuNulo(valor.detalhe)
  );
}

function eQuem(valor: unknown): valor is Quem {
  return eObjeto(valor) && eUmDe(TIPOS_DE_QUEM, valor.tipo) && eTexto(valor.nome);
}

function eAlvo(valor: unknown): valor is Alvo {
  if (!eObjeto(valor) || !eUmDe(TIPOS_DE_ALVO, valor.tipo) || !eTexto(valor.nome)) return false;
  const { parametros } = valor;
  return (
    eObjeto(parametros) &&
    Object.values(parametros).every((p) => typeof p === "string" || Number.isInteger(p))
  );
}

/** A resposta de um cenário; no permitido, sem mensagem. */
export function eResposta(valor: unknown, obtido: Desfecho): valor is Resposta {
  if (!eObjeto(valor)) return false;
  const { status, mensagem, linhas } = valor;
  const statusValido = status === null || (Number.isInteger(status) && (status as number) >= 100);
  if (!statusValido || !eTextoOuNulo(mensagem) || !eContagemOuNula(linhas)) return false;
  return obtido === "negado" || mensagem === null;
}

export function eLinhaDaAuditoria(valor: unknown): valor is LinhaDaAuditoria {
  if (!eObjeto(valor)) return false;
  return (
    eContagem(valor.id) &&
    eInstante(valor.horario) &&
    eTexto(valor.usuario) &&
    eTexto(valor.ferramenta) &&
    (valor.argumentos === null || eObjeto(valor.argumentos)) &&
    eTexto(valor.resultado)
  );
}

export function eCenarioDeSeguranca(valor: unknown): valor is CenarioDeSeguranca {
  if (!eObjeto(valor)) return false;
  const { camadas_de_defesa: camadas, obtido } = valor;
  return (
    eTexto(valor.id) &&
    eTexto(valor.descricao) &&
    eUmDe(GRUPOS, valor.grupo) &&
    eQuem(valor.quem) &&
    (valor.perfil === null || ePerfil(valor.perfil)) &&
    eAlvo(valor.alvo) &&
    Array.isArray(camadas) &&
    camadas.length > 0 &&
    camadas.every((camada) => eUmDe(CAMADAS_DE_DEFESA, camada)) &&
    eUmDe(DESFECHOS, valor.esperado) &&
    eUmDe(DESFECHOS, obtido) &&
    typeof valor.divergencia === "boolean" &&
    eResposta(valor.resposta, obtido) &&
    (valor.auditoria === null || eLinhaDaAuditoria(valor.auditoria)) &&
    eContagem(valor.duracao_em_ms)
  );
}

export function eExecucaoDeAceite(valor: unknown): valor is ExecucaoDeAceite {
  if (!eObjeto(valor)) return false;
  const { cenarios, resumo } = valor;
  return (
    eInstante(valor.executada_em) &&
    eContagemDoResumo(resumo) &&
    (valor.matriz_completa === null || eMatrizCompleta(valor.matriz_completa)) &&
    (valor.carga === null || eConferenciaDaCarga(valor.carga)) &&
    Array.isArray(cenarios) &&
    cenarios.every(eCenarioDeSeguranca) &&
    resumo.executados === cenarios.length
  );
}

export function ePainelDeSeguranca(valor: unknown): valor is PainelDeSeguranca {
  return eObjeto(valor) && (valor.execucao === null || eExecucaoDeAceite(valor.execucao));
}

/** Os cenários agrupados pelo grupo da matriz, na ordem dos grupos; grupo vazio fica de fora. */
export function agruparPorGrupo(
  cenarios: readonly CenarioDeSeguranca[],
): { grupo: Grupo; cenarios: CenarioDeSeguranca[] }[] {
  return GRUPOS.map((grupo) => ({
    grupo,
    cenarios: cenarios.filter((cenario) => cenario.grupo === grupo),
  })).filter(({ cenarios: doGrupo }) => doGrupo.length > 0);
}
