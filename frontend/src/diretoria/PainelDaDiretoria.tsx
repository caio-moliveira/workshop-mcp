import { PageHeading } from "../componentes/PageHeading";
import { PeriodFilter } from "../componentes/PeriodFilter";
import { usePeriodoDaUrl } from "../painel/usePeriodoDaUrl";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import type { FonteDeDados } from "../useBloco";
import { BlocoDeIndicadores } from "./BlocoDeIndicadores";
import { BlocoDosFatoresDeRecompra } from "./BlocoDosFatoresDeRecompra";
import { ResumoPorCanalDoLojista } from "./BlocoDoResumoPorCanal";

interface Propriedades {
  fonte: FonteDeDados;
  primeiroNome: string;
}

/**
 * O painel da Diretoria (FE §6): só indicadores consolidados, nunca um registro individual. Cada
 * bloco busca a própria rota com o período da URL; trocar o período atualiza a URL e recarrega
 * todos os blocos juntos, como nos outros painéis.
 */
export function PainelDaDiretoria({ fonte, primeiroNome }: Propriedades) {
  const [periodo, mudarPeriodo] = usePeriodoDaUrl();
  const { nome, rotuloDoPainel } = DESCRICAO_DOS_PERFIS.diretoria;
  return (
    <>
      <PageHeading
        contexto={nome}
        titulo={rotuloDoPainel}
        subtitulo={`Olá, ${primeiroNome}. Receita, recompra, satisfação e retenção do período, até a data de referência dos dados.`}
        controles={<PeriodFilter periodo={periodo} aoMudar={mudarPeriodo} />}
      />
      <BlocoDeIndicadores fonte={fonte} periodo={periodo} />
      <BlocoDosFatoresDeRecompra fonte={fonte} periodo={periodo} />
      <ResumoPorCanalDoLojista fonte={fonte} periodo={periodo} />
    </>
  );
}
