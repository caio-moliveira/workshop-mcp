import type { User, UserManager } from "oidc-client-ts";

import {
  apagarNaApi,
  ApiIndisponivel,
  buscarDaApi,
  buscarEu,
  TokenRecusado,
  type UsuarioAutenticado,
} from "../api";
import { eConversaLida, type ConversaLida } from "../assistente/conversa";
import type { EventoDaResposta } from "../assistente/fluxo";
import { perguntarAoAssistente, type CorpoDaPergunta } from "../assistente/rede";
import { VigiaDeInatividade } from "./inatividade";

export type EstadoDaSessao =
  /** Confirmando quem é o usuário: voltando do login, renovando em silêncio ou pedindo `/eu`. */
  | { fase: "confirmando" }
  /** A API reconheceu o usuário. */
  | { fase: "pronta"; usuario: UsuarioAutenticado }
  /** A API está fora do ar; a sessão pode estar boa. */
  | { fase: "indisponivel" }
  /** A API recusou o token que o provedor acabou de emitir: entrar de novo não resolveria. */
  | { fase: "recusada" }
  /** Saindo da aplicação, rumo à tela de login do provedor. */
  | { fase: "redirecionando" };

/**
 * A sessão do usuário na aplicação, por cima do cliente OIDC.
 *
 * Entra pelo login do provedor, volta em silêncio ao recarregar a página e confirma o usuário em
 * `GET /eu`. Renova o token só de quem usa a aplicação: cada renovação prorroga a sessão do
 * provedor, então renovar sempre a manteria viva para sempre. Sem nenhuma interação durante o
 * tempo de inatividade, encerra a sessão também no provedor e volta à tela de login.
 */
export class Sessao {
  private estado: EstadoDaSessao = { fase: "confirmando" };
  private readonly ouvintes = new Set<() => void>();
  private readonly vigia: VigiaDeInatividade;
  private iniciada = false;
  /** Quando o token atual chegou: só renova quem interagiu depois disso. */
  private tokenObtidoEm = 0;
  /** O token está para vencer (ou venceu) sem interação: renova na próxima. */
  private renovacaoPendente = false;
  /** A renovação em andamento: quem pede um token durante ela espera a mesma. */
  private renovacao: Promise<void> | null = null;
  /** A API já aceitou um token nesta carga da página. */
  private apiJaAceitou = false;

  constructor(
    private readonly gerenciador: UserManager,
    private readonly enderecoDaApi: string,
    inatividadeEmSegundos: number,
  ) {
    this.vigia = new VigiaDeInatividade(
      inatividadeEmSegundos * 1000,
      () => void this.sair(),
      () => {
        if (this.renovacaoPendente) void this.renovar();
      },
    );
    gerenciador.events.addAccessTokenExpiring(() => {
      if (this.vigia.interagiuDepoisDe(this.tokenObtidoEm)) void this.renovar();
      else this.renovacaoPendente = true;
    });
  }

  obterEstado = (): EstadoDaSessao => this.estado;

  inscrever = (ouvinte: () => void): (() => void) => {
    this.ouvintes.add(ouvinte);
    return () => this.ouvintes.delete(ouvinte);
  };

  /** Roda uma vez por carga da página. */
  async iniciar(): Promise<void> {
    if (this.iniciada) return;
    this.iniciada = true;
    const usuario = (await this.voltarDoLogin()) ?? (await this.voltarEmSilencio());
    if (!usuario) return this.irParaOLogin();
    this.tokenObtidoEm = Date.now();
    await this.confirmar(usuario.access_token);
  }

  async tentarDeNovo(): Promise<void> {
    this.mudar({ fase: "confirmando" });
    const usuario = await this.gerenciador.getUser();
    if (!usuario || usuario.expired) return this.irParaOLogin();
    await this.confirmar(usuario.access_token);
  }

  /**
   * Pede uma rota de dados com o token atual e valida a resposta, pelas regras de `comToken`.
   */
  consultar<T>(caminho: string, validar: (valor: unknown) => valor is T): Promise<T> {
    return this.comToken((token) => buscarDaApi(this.enderecoDaApi, token, caminho, validar));
  }

  /**
   * Faz uma pergunta ao assistente com o token atual e devolve os eventos da resposta. O token
   * segue as regras de `comToken`, inclusive no 401 antes do fluxo.
   */
  async *perguntar(corpo: CorpoDaPergunta, sinal?: AbortSignal): AsyncGenerator<EventoDaResposta> {
    yield* await this.comToken((token) =>
      perguntarAoAssistente(this.enderecoDaApi, token, corpo, sinal),
    );
  }

  /** As conversas do usuário, como a API as devolve; quem confere o contrato é `listaRecebida`. */
  listarConversas(): Promise<object> {
    return this.consultar(
      "/conversas",
      (valor): valor is object => typeof valor === "object" && valor !== null,
    );
  }

  /** Uma conversa do histórico, no contrato. A de outro usuário não vem: é ApiIndisponivel. */
  lerConversa(id: string): Promise<ConversaLida> {
    return this.consultar(`/conversas/${encodeURIComponent(id)}`, eConversaLida);
  }

  /** Apaga uma conversa do histórico, de modo definitivo. */
  apagarConversa(id: string): Promise<void> {
    return this.comToken((token) =>
      apagarNaApi(this.enderecoDaApi, token, `/conversas/${encodeURIComponent(id)}`),
    );
  }

  /**
   * Chama a API com o token atual. Um token vencido é renovado antes; um 401 segue o fluxo de
   * sessão (volta ao login) e chega a quem pediu como TokenRecusado.
   */
  private async comToken<T>(chamar: (token: string) => Promise<T>): Promise<T> {
    const token = await this.tokenAtual();
    try {
      return await chamar(token);
    } catch (erro) {
      if (erro instanceof TokenRecusado) await this.aoRecusarToken();
      throw erro;
    }
  }

  /** O token em vigor, renovado antes se venceu. Sem token, vai ao login e lança TokenRecusado. */
  private async tokenAtual(): Promise<string> {
    let usuario = await this.gerenciador.getUser();
    if (!usuario || usuario.expired) {
      await this.renovar();
      usuario = await this.gerenciador.getUser();
    }
    if (!usuario || usuario.expired) {
      await this.irParaOLogin();
      throw new TokenRecusado();
    }
    return usuario.access_token;
  }

  /** Encerra a sessão também no provedor e volta à tela de login. */
  async sair(): Promise<void> {
    this.vigia.parar();
    this.mudar({ fase: "redirecionando" });
    try {
      await this.gerenciador.signoutRedirect();
    } catch {
      await this.irParaOLogin();
    }
  }

  private async irParaOLogin(): Promise<void> {
    this.vigia.parar();
    this.mudar({ fase: "redirecionando" });
    await this.gerenciador.removeUser();
    // A busca da URL (o período, por exemplo) volta junto do login, pelo estado do pedido.
    await this.gerenciador.signinRedirect({ state: { busca: window.location.search } });
  }

  /** Troca o refresh token por um token novo, o que também prorroga a sessão do provedor. */
  private renovar(): Promise<void> {
    this.renovacao ??= this.renovarUmaVez().finally(() => {
      this.renovacao = null;
    });
    return this.renovacao;
  }

  private async renovarUmaVez(): Promise<void> {
    this.renovacaoPendente = false;
    try {
      if (!(await this.gerenciador.signinSilent())) throw new Error("renovação sem usuário");
      this.tokenObtidoEm = Date.now();
    } catch {
      // A sessão do provedor acabou (duração máxima, saída em outra aba): entrar de novo.
      await this.irParaOLogin();
    }
  }

  /** O provedor devolveu o usuário com um código de autorização: troca pelo token. */
  private async voltarDoLogin(): Promise<User | null> {
    const parametros = new URLSearchParams(window.location.search);
    if (!parametros.has("state") || !(parametros.has("code") || parametros.has("error"))) {
      return null;
    }
    let busca = "";
    try {
      const usuario = await this.gerenciador.signinRedirectCallback();
      busca = buscaGuardada(usuario.state);
      return usuario;
    } catch {
      return null;
    } finally {
      // O código é de uso único e não deve ficar na barra de endereço nem no histórico. A busca
      // de antes do login (o período, por exemplo) volta ao lugar dele.
      window.history.replaceState(null, "", `${window.location.pathname}${busca}`);
    }
  }

  /** Página recarregada: o token em memória se foi, mas a sessão do provedor pode seguir ativa. */
  private async voltarEmSilencio(): Promise<User | null> {
    try {
      return await this.gerenciador.signinSilent();
    } catch {
      return null;
    }
  }

  private async confirmar(token: string): Promise<void> {
    try {
      const usuario = await buscarEu(this.enderecoDaApi, token);
      this.apiJaAceitou = true;
      this.mudar({ fase: "pronta", usuario });
      this.vigia.iniciar();
    } catch (erro) {
      if (erro instanceof TokenRecusado) return this.aoRecusarToken();
      if (erro instanceof ApiIndisponivel) return this.mudar({ fase: "indisponivel" });
      throw erro;
    }
  }

  /**
   * Regra contra o laço de login. Voltar ao login só ajuda se a API já aceitou um token nesta
   * carga da página: o token de agora é outro, e um novo pode servir. Se ela recusou de cara o
   * token que o provedor acabou de emitir, voltar ao login não muda nada: com a sessão do provedor
   * ativa, o login volta em silêncio com um token igual, a API recusa de novo e a página entra
   * num laço. Nesse caso, mostra o erro com a ação de sair, que encerra a sessão no provedor.
   * Como ir ao login recarrega a página, cada recusa leva ao login no máximo uma vez.
   */
  private async aoRecusarToken(): Promise<void> {
    if (this.apiJaAceitou) return this.irParaOLogin();
    this.mudar({ fase: "recusada" });
  }

  private mudar(estado: EstadoDaSessao): void {
    this.estado = estado;
    this.ouvintes.forEach((ouvinte) => ouvinte());
  }
}

/** A busca da URL guardada no estado do pedido de login, se for uma busca. */
function buscaGuardada(estado: unknown): string {
  if (typeof estado !== "object" || estado === null) return "";
  const { busca } = estado as Record<string, unknown>;
  return typeof busca === "string" && busca.startsWith("?") ? busca : "";
}
