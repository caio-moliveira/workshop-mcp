import type { User, UserManager } from "oidc-client-ts";

import { ApiIndisponivel, buscarEu, SessaoRecusada, type Eu } from "../api";

export type EstadoDaSessao =
  /** Confirmando quem é o usuário: voltando do login, renovando em silêncio ou pedindo `/eu`. */
  | { fase: "confirmando" }
  /** A API reconheceu o usuário. */
  | { fase: "pronta"; eu: Eu }
  /** A API está fora do ar; a sessão pode estar boa. */
  | { fase: "indisponivel" }
  /** Saindo da aplicação, rumo à tela de login do provedor. */
  | { fase: "redirecionando" };

/**
 * A sessão do usuário na aplicação, por cima do cliente OIDC.
 *
 * Entra pelo login do provedor, volta em silêncio ao recarregar a página, confirma o usuário em
 * `GET /eu` e leva de volta ao login quando a renovação falha ou a API recusa o token.
 */
export class Sessao {
  private estado: EstadoDaSessao = { fase: "confirmando" };
  private readonly ouvintes = new Set<() => void>();
  private iniciada = false;

  constructor(
    private readonly gerenciador: UserManager,
    private readonly enderecoDaApi: string,
  ) {
    // A renovação automática falhou (sessão do provedor expirada ou encerrada): de volta ao login.
    gerenciador.events.addSilentRenewError(() => void this.irParaOLogin());
    gerenciador.events.addAccessTokenExpired(() => void this.irParaOLogin());
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
    await this.confirmar(usuario.access_token);
  }

  async tentarDeNovo(): Promise<void> {
    this.mudar({ fase: "confirmando" });
    const usuario = await this.gerenciador.getUser();
    if (!usuario || usuario.expired) return this.irParaOLogin();
    await this.confirmar(usuario.access_token);
  }

  /** Encerra a sessão também no provedor e volta à tela de login. */
  async sair(): Promise<void> {
    this.mudar({ fase: "redirecionando" });
    try {
      await this.gerenciador.signoutRedirect();
    } catch {
      await this.irParaOLogin();
    }
  }

  private async irParaOLogin(): Promise<void> {
    this.mudar({ fase: "redirecionando" });
    await this.gerenciador.removeUser();
    await this.gerenciador.signinRedirect();
  }

  /** O provedor devolveu o usuário com um código de autorização: troca pelo token. */
  private async voltarDoLogin(): Promise<User | null> {
    const parametros = new URLSearchParams(window.location.search);
    if (!parametros.has("state") || !(parametros.has("code") || parametros.has("error"))) {
      return null;
    }
    try {
      return await this.gerenciador.signinRedirectCallback();
    } catch {
      return null;
    } finally {
      // O código é de uso único e não deve ficar na barra de endereço nem no histórico.
      window.history.replaceState(null, "", window.location.pathname);
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
      this.mudar({ fase: "pronta", eu: await buscarEu(this.enderecoDaApi, token) });
    } catch (erro) {
      if (erro instanceof SessaoRecusada) return this.irParaOLogin();
      if (erro instanceof ApiIndisponivel) return this.mudar({ fase: "indisponivel" });
      throw erro;
    }
  }

  private mudar(estado: EstadoDaSessao): void {
    this.estado = estado;
    this.ouvintes.forEach((ouvinte) => ouvinte());
  }
}
