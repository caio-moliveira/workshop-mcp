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
 * sessão do provedor estiver ativa. A renovação usa o refresh token, também em memória.
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
    // Renova um minuto antes de vencer (o token de acesso dura 5 minutos).
    automaticSilentRenew: true,
    accessTokenExpiringNotificationTimeInSeconds: 60,
    monitorSession: false,
  });
}
