import { ePerfil, type Perfil } from "./perfis";

/** O usuário como a API o reconhece. Nome e perfil nunca vêm do token decodificado. */
export interface UsuarioAutenticado {
  nome: string;
  perfil: Perfil;
}

/** A API recusou o token (401). O que fazer depende de quando: veja `Sessao.aoRecusarToken`. */
export class TokenRecusado extends Error {
  constructor() {
    super("A API recusou o token.");
    this.name = "TokenRecusado";
  }
}

/** A API negou o acesso aos dados (403): o perfil do usuário não lê esta rota. */
export class AcessoNegado extends Error {
  constructor() {
    super("A API negou o acesso.");
    this.name = "AcessoNegado";
  }
}

/** A API não respondeu ou respondeu algo inesperado: não é culpa da sessão. */
export class ApiIndisponivel extends Error {
  constructor(motivo: string) {
    super(motivo);
    this.name = "ApiIndisponivel";
  }
}

/**
 * Pede uma rota da API com o token no cabeçalho Authorization e valida a resposta antes do uso.
 * `caminho` já traz a busca (`/vendas/indicadores?periodo=12m`). Uma resposta fora do contrato é
 * tratada como indisponibilidade, nunca como dado.
 */
export async function buscarDaApi<T>(
  enderecoDaApi: string,
  token: string,
  caminho: string,
  validar: (valor: unknown) => valor is T,
): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(`${enderecoDaApi}${caminho}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (erro) {
    throw new ApiIndisponivel(`sem resposta da API: ${String(erro)}`);
  }
  if (resposta.status === 401) throw new TokenRecusado();
  if (resposta.status === 403) throw new AcessoNegado();
  if (!resposta.ok) throw new ApiIndisponivel(`a API respondeu ${resposta.status}`);
  let corpo: unknown;
  try {
    corpo = await resposta.json();
  } catch {
    throw new ApiIndisponivel(`resposta de ${caminho} não é JSON`);
  }
  if (!validar(corpo)) throw new ApiIndisponivel(`resposta de ${caminho} fora do contrato`);
  return corpo;
}

function eUsuarioAutenticado(valor: unknown): valor is UsuarioAutenticado {
  if (typeof valor !== "object" || valor === null) return false;
  const { nome, perfil } = valor as Record<string, unknown>;
  return typeof nome === "string" && ePerfil(perfil);
}

/** Pede `GET /eu` com o token no cabeçalho Authorization. */
export function buscarEu(enderecoDaApi: string, token: string): Promise<UsuarioAutenticado> {
  return buscarDaApi(enderecoDaApi, token, "/eu", eUsuarioAutenticado);
}
