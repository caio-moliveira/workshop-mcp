import { PageHeading } from "../componentes/PageHeading";
import { PeriodFilter } from "../componentes/PeriodFilter";
import { usePeriodoDaUrl } from "../painel/usePeriodoDaUrl";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import type { FonteDeDados } from "../useBloco";
import { BlocoDeIndicadores } from "./BlocoDeIndicadores";
import { BlocoDeMalAvaliados } from "./BlocoDeMalAvaliados";

interface Propriedades {
  fonte: FonteDeDados;
  primeiroNome: string;
}

/**
 * O painel de Produtos (FE §6). Cada bloco busca a própria rota com o período da URL; trocar o
 * período atualiza a URL e recarrega todos os blocos juntos, como em Vendas.
 */
export function PainelDeProdutos({ fonte, primeiroNome }: Propriedades) {
  const [periodo, mudarPeriodo] = usePeriodoDaUrl();
  const { nome, rotuloDoPainel } = DESCRICAO_DOS_PERFIS.produtos;
  return (
    <>
      <PageHeading
        contexto={nome}
        titulo={rotuloDoPainel}
        subtitulo={`Olá, ${primeiroNome}. Catálogo, notas e reclamações das avaliações do período, até a data de referência dos dados.`}
        controles={<PeriodFilter periodo={periodo} aoMudar={mudarPeriodo} />}
      />
      <BlocoDeIndicadores fonte={fonte} periodo={periodo} />
      <BlocoDeMalAvaliados fonte={fonte} periodo={periodo} />
    </>
  );
}
