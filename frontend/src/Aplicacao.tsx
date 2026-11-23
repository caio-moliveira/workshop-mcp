import { useSyncExternalStore } from "react";

import { AppShell } from "./componentes/AppShell";
import { EmptyState } from "./componentes/EmptyState";
import { ErrorState } from "./componentes/ErrorState";
import { LoadingSkeleton } from "./componentes/LoadingSkeleton";
import { PageHeading } from "./componentes/PageHeading";
import { DESCRICAO_DOS_PERFIS } from "./perfis";
import type { Sessao } from "./sessao/sessao";

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
          aoTentarDeNovo={() => void sessao.tentarDeNovo()}
        />
      );
    case "pronta": {
      const { eu } = estado;
      const perfil = DESCRICAO_DOS_PERFIS[eu.perfil];
      return (
        <AppShell eu={eu} aoSair={() => void sessao.sair()}>
          <PageHeading
            contexto={perfil.nome}
            titulo={perfil.area}
            subtitulo={`Olá, ${eu.nome.split(" ")[0]}. Aqui você acompanha os dados do seu perfil.`}
          />
          <EmptyState
            titulo="O painel chega em breve"
            descricao={`Os indicadores de ${perfil.nome} aparecem aqui na próxima entrega. Seu acesso já está pronto.`}
          />
        </AppShell>
      );
    }
  }
}
