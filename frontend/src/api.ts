import { ePerfil, type Perfil } from "./perfis";

/** O usuário como a API o reconhece. Nome e perfil nunca vêm do token decodificado. */
export interface Eu {
  nome: string;
  perfil: Perfil;
}

/** A API recusou o token (401): a sessão acabou e o usuário precisa entrar de novo. */
export class SessaoRecusada extends Error {
  constructor() {
    super("A API recusou o token.");
    this.name = "SessaoRecusada";
  }
}

/** A API não respondeu ou respondeu algo inesperado: não é culpa da sessão. */
export class ApiIndisponivel extends Error {
  constructor(motivo: string) {
    super(motivo);
    this.name = "ApiIndisponivel";
  }
}

function eEu(valor: unknown): valor is Eu {
  if (typeof valor !== "object" || valor === null) return false;
  const { nome, perfil } = valor as Record<string, unknown>;
  return typeof nome === "string" && ePerfil(perfil);
}

/** Pede `GET /eu` com o token no cabeçalho Authorization. */
export async function buscarEu(enderecoDaApi: string, token: string): Promise<Eu> {
  let resposta: Response;
  try {
    resposta = await fetch(`${enderecoDaApi}/eu`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (erro) {
    throw new ApiIndisponivel(`sem resposta da API: ${String(erro)}`);
  }
  if (resposta.status === 401) throw new SessaoRecusada();
  if (!resposta.ok) throw new ApiIndisponivel(`a API respondeu ${resposta.status}`);
  const corpo: unknown = await resposta.json();
  if (!eEu(corpo)) throw new ApiIndisponivel("resposta de /eu fora do contrato");
  return corpo;
}
