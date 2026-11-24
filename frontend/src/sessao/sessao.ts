import type { User, UserManager } from "oidc-client-ts";

import { ApiIndisponivel, buscarEu, TokenRecusado, type UsuarioAutenticado } from "../api";
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
  private renovando = false;
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
    await this.gerenciador.signinRedirect();
  }

  /** Troca o refresh token por um token novo, o que também prorroga a sessão do provedor. */
  private async renovar(): Promise<void> {
    if (this.renovando) return;
    this.renovando = true;
    this.renovacaoPendente = false;
    try {
      if (!(await this.gerenciador.signinSilent())) throw new Error("renovação sem usuário");
      this.tokenObtidoEm = Date.now();
    } catch {
      // A sessão do provedor acabou (duração máxima, saída em outra aba): entrar de novo.
      await this.irParaOLogin();
    } finally {
      this.renovando = false;
    }
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
