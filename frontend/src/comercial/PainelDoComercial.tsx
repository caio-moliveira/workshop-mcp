import { PageHeading } from "../componentes/PageHeading";
import { PeriodFilter } from "../componentes/PeriodFilter";
import linha from "../painel/LinhaAnalitica.module.css";
import { usePeriodoDaUrl } from "../painel/usePeriodoDaUrl";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import type { FonteDeDados } from "../useBloco";
import { BlocoDeDesempenhoDosCanais } from "./BlocoDeDesempenhoDosCanais";
import { BlocoDeIndicadores } from "./BlocoDeIndicadores";
import { BlocoDeNovosLojistasPorCanal } from "./BlocoDeNovosLojistasPorCanal";

interface Propriedades {
  fonte: FonteDeDados;
  primeiroNome: string;
}

/**
 * O painel do Comercial (FE §6). Cada bloco busca a própria rota com o período da URL; trocar o
 * período atualiza a URL e recarrega todos os blocos juntos, como em Vendas e Produtos.
 */
export function PainelDoComercial({ fonte, primeiroNome }: Propriedades) {
  const [periodo, mudarPeriodo] = usePeriodoDaUrl();
  const { nome, rotuloDoPainel } = DESCRICAO_DOS_PERFIS.comercial;
  return (
    <>
      <PageHeading
        contexto={nome}
        titulo={rotuloDoPainel}
        subtitulo={`Olá, ${primeiroNome}. Leads, novos lojistas e conversão do período, até a data de referência dos dados.`}
        controles={<PeriodFilter periodo={periodo} aoMudar={mudarPeriodo} />}
      />
      <BlocoDeIndicadores fonte={fonte} periodo={periodo} />
      <div className={linha.linhaAnalitica}>
        <div className={linha.complementar}>
          <BlocoDeNovosLojistasPorCanal fonte={fonte} periodo={periodo} />
        </div>
      </div>
      <BlocoDeDesempenhoDosCanais fonte={fonte} periodo={periodo} />
    </>
  );
}
