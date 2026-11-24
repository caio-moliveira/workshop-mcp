import { InMemoryWebStorage, UserManager, WebStorageStateStore } from "oidc-client-ts";

/** Realm e cliente público do provedor (keycloak/realm/pulso.json). */
export const REALM = "pulso";
export const APLICACAO = "pulso-web";

export const RETORNO_DO_LOGIN = `${window.location.origin}/`;
export const RETORNO_DA_RENOVACAO = `${window.location.origin}/renovacao.html`;

/**
 * O cliente OIDC do navegador: fluxo de código com PKCE (S256), sem segredo (ADR 0004).
 *
 * O token fica só em memória. Recarregar a página o apaga, e a volta é silenciosa enquanto a
 * sessão do provedor estiver ativa. A renovação usa o refresh token, também em memória, e é
 * pedida pela Sessao.
 */
export function criarGerenciador(enderecoDoProvedor: string): UserManager {
  return new UserManager({
    authority: `${enderecoDoProvedor}/realms/${REALM}`,
    client_id: APLICACAO,
    redirect_uri: RETORNO_DO_LOGIN,
    silent_redirect_uri: RETORNO_DA_RENOVACAO,
    post_logout_redirect_uri: RETORNO_DO_LOGIN,
    response_type: "code",
    scope: "openid",
    userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
    // Sem renovação automática: renovar mantém viva a sessão do provedor, e a Sessao só renova o
    // token de quem usou a aplicação (sessao.ts). O aviso vem um minuto antes de o token vencer
    // (ele dura 5 minutos).
    automaticSilentRenew: false,
    accessTokenExpiringNotificationTimeInSeconds: 60,
    monitorSession: false,
  });
}
