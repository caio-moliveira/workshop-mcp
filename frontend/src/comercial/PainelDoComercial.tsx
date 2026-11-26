import { PageHeading } from "../componentes/PageHeading";
import { PeriodFilter } from "../componentes/PeriodFilter";
import linha from "../painel/LinhaAnalitica.module.css";
import { usePeriodoDaUrl } from "../painel/usePeriodoDaUrl";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import { useBloco, type FonteDeDados } from "../useBloco";
import { BlocoDeDesempenhoDosCanais } from "./BlocoDeDesempenhoDosCanais";
import { BlocoDeIndicadores } from "./BlocoDeIndicadores";
import { BlocoDeNovosLojistasPorCanal } from "./BlocoDeNovosLojistasPorCanal";
import { BlocoDoFunil } from "./BlocoDoFunil";
import { BlocoDeLeadsRecentes } from "./BlocoDeLeadsRecentes";
import { eDesempenhoDosCanais, rotaDosCanais } from "./desempenhoDosCanais";

interface Propriedades {
  fonte: FonteDeDados;
  primeiroNome: string;
}

/**
 * O painel do Comercial (FE §6). Cada bloco busca a própria rota com o período da URL, menos o
 * gráfico de novos lojistas por canal e a tabela de desempenho dos canais: os dois mostram a mesma
 * rota, que o painel busca uma vez e entrega aos dois, e por isso carregam, falham e tentam de novo
 * juntos. Trocar o período atualiza a URL e recarrega todos os blocos juntos, como em Vendas e
 * Produtos.
 */
export function PainelDoComercial({ fonte, primeiroNome }: Propriedades) {
  const [periodo, mudarPeriodo] = usePeriodoDaUrl();
  const { nome, rotuloDoPainel } = DESCRICAO_DOS_PERFIS.comercial;
  const canais = useBloco(fonte, rotaDosCanais(periodo), eDesempenhoDosCanais);
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
        <div className={linha.principal}>
          <BlocoDoFunil fonte={fonte} periodo={periodo} />
        </div>
        <div className={linha.complementar}>
          <BlocoDeNovosLojistasPorCanal {...canais} />
        </div>
      </div>
      <BlocoDeDesempenhoDosCanais {...canais} />
      <BlocoDeLeadsRecentes fonte={fonte} periodo={periodo} />
    </>
  );
}
