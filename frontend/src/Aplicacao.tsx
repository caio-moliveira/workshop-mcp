import { useSyncExternalStore } from "react";

import { AppShell } from "./componentes/AppShell";
import { EmptyState } from "./componentes/EmptyState";
import { ErrorState } from "./componentes/ErrorState";
import { LoadingSkeleton } from "./componentes/LoadingSkeleton";
import { PageHeading } from "./componentes/PageHeading";
import { DESCRICAO_DOS_PERFIS } from "./perfis";
import type { Sessao } from "./sessao/sessao";
import { PainelDeVendas } from "./vendas/PainelDeVendas";

export function Aplicacao({ sessao }: { sessao: Sessao }) {
  const estado = useSyncExternalStore(sessao.inscrever, sessao.obterEstado);

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
      const perfil = DESCRICAO_DOS_PERFIS[usuario.perfil];
      const primeiroNome = usuario.nome.split(" ")[0] ?? usuario.nome;
      return (
        <AppShell usuario={usuario} assistente={sessao} aoSair={() => void sessao.sair()}>
          {usuario.perfil === "vendas" ? (
            <PainelDeVendas fonte={sessao} primeiroNome={primeiroNome} />
          ) : (
            <>
              <PageHeading
                contexto={perfil.nome}
                titulo={perfil.rotuloDoPainel}
                subtitulo={`Olá, ${primeiroNome}. Aqui você acompanha os dados do seu perfil.`}
              />
              <EmptyState
                titulo="O painel chega em breve"
                descricao={`Os indicadores de ${perfil.nome} aparecem aqui em uma das próximas entregas. Seu acesso já está pronto.`}
              />
            </>
          )}
        </AppShell>
      );
    }
  }
}
