import { PageHeading } from "../componentes/PageHeading";
import { PeriodFilter } from "../componentes/PeriodFilter";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import type { FonteDeDados } from "../useBloco";
import { BlocoDeIndicadores } from "./BlocoDeIndicadores";
import { BlocoDePedidosRecentes } from "./BlocoDePedidosRecentes";
import { usePeriodoDaUrl } from "./usePeriodoDaUrl";

interface Propriedades {
  fonte: FonteDeDados;
  primeiroNome: string;
}

/**
 * O painel de Vendas (FE §6). Cada bloco busca a própria rota com o período da URL; trocar o
 * período atualiza a URL e recarrega todos os blocos juntos.
 */
export function PainelDeVendas({ fonte, primeiroNome }: Propriedades) {
  const [periodo, mudarPeriodo] = usePeriodoDaUrl();
  const { nome, rotuloDoPainel } = DESCRICAO_DOS_PERFIS.vendas;
  return (
    <>
      <PageHeading
        contexto={nome}
        titulo={rotuloDoPainel}
        subtitulo={`Olá, ${primeiroNome}. Pedidos, receita, atrasos e pagamentos do período, até a data de referência dos dados.`}
        filtros={<PeriodFilter periodo={periodo} aoMudar={mudarPeriodo} />}
      />
      <BlocoDeIndicadores fonte={fonte} periodo={periodo} />
      <BlocoDePedidosRecentes fonte={fonte} periodo={periodo} />
    </>
  );
}
