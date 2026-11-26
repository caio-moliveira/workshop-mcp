import { useSyncExternalStore } from "react";

import { PainelDoComercial } from "./comercial/PainelDoComercial";
import { AppShell } from "./componentes/AppShell";
import { ErrorState } from "./componentes/ErrorState";
import { LoadingSkeleton } from "./componentes/LoadingSkeleton";
import { PainelDaDiretoria } from "./diretoria/PainelDaDiretoria";
import { PAGINA_DE_SEGURANCA, usePagina } from "./navegacao";
import { PainelDeProdutos } from "./produtos/PainelDeProdutos";
import { PainelDeSeguranca } from "./seguranca/PainelDeSeguranca";
import type { Sessao } from "./sessao/sessao";
import { PainelDeVendas } from "./vendas/PainelDeVendas";

export function Aplicacao({ sessao }: { sessao: Sessao }) {
  const estado = useSyncExternalStore(sessao.inscrever, sessao.obterEstado);
  const pagina = usePagina();

  switch (estado.fase) {
    case "confirmando":
    case "redirecionando":
      return <LoadingSkeleton />;
    case "indisponivel":
      return (
        <ErrorState
          titulo="O pulso. está fora do ar"
          descricao="Não conseguimos falar com o servidor agora. Sua sessão continua ativa."
          acao="Tentar de novo"
          aoAcionar={() => void sessao.tentarDeNovo()}
        />
      );
    case "recusada":
      return (
        <ErrorState
          titulo="Não foi possível confirmar seu acesso"
          descricao="O servidor não aceitou a sua entrada. Saia e entre de novo; se continuar, fale com quem administra o pulso."
          acao="Sair"
          aoAcionar={() => void sessao.sair()}
        />
      );
    case "pronta": {
      const { usuario } = estado;
      const primeiroNome = usuario.nome.split(" ")[0] ?? usuario.nome;
      // Sem o interruptor de demonstração, /seguranca mostra o painel do perfil, como qualquer
      // outro caminho.
      const naSeguranca = usuario.painel_de_seguranca === true && pagina === PAGINA_DE_SEGURANCA;
      return (
        <AppShell usuario={usuario} assistente={sessao} aoSair={() => void sessao.sair()}>
          {naSeguranca ? (
            <PainelDeSeguranca fonte={sessao} />
          ) : usuario.perfil === "vendas" ? (
            <PainelDeVendas fonte={sessao} primeiroNome={primeiroNome} />
          ) : usuario.perfil === "produtos" ? (
            <PainelDeProdutos fonte={sessao} primeiroNome={primeiroNome} />
          ) : usuario.perfil === "comercial" ? (
            <PainelDoComercial fonte={sessao} primeiroNome={primeiroNome} />
          ) : (
            <PainelDaDiretoria fonte={sessao} primeiroNome={primeiroNome} />
          )}
        </AppShell>
      );
    }
  }
}
