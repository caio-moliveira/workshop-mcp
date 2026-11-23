import { UserManager } from "oidc-client-ts";

import { APLICACAO, RETORNO_DA_RENOVACAO } from "./gerenciador";

/*
 * Roda dentro do iframe oculto da renovação silenciosa (ao recarregar a página, quando ainda não
 * há refresh token em memória). Só entrega à janela da aplicação o endereço com a resposta do
 * provedor; a troca do código pelo token acontece lá. Por isso não precisa do endereço real do
 * provedor, só de uma configuração válida.
 */
void new UserManager({
  authority: window.location.origin,
  client_id: APLICACAO,
  redirect_uri: RETORNO_DA_RENOVACAO,
}).signinSilentCallback();
