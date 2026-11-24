import { PageHeading } from "../componentes/PageHeading";
import { PeriodFilter } from "../componentes/PeriodFilter";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import type { FonteDeDados } from "../useBloco";
import { BlocoDeEvolucao } from "./BlocoDeEvolucao";
import { BlocoDeIndicadores } from "./BlocoDeIndicadores";
import { BlocoDePedidosRecentes } from "./BlocoDePedidosRecentes";
import { BlocoDeSituacaoDasEntregas } from "./BlocoDeSituacaoDasEntregas";
import estilos from "./PainelDeVendas.module.css";
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
        controles={<PeriodFilter periodo={periodo} aoMudar={mudarPeriodo} />}
      />
      <BlocoDeIndicadores fonte={fonte} periodo={periodo} />
      <div className={estilos.linhaAnalitica}>
        <div className={estilos.principal}>
          <BlocoDeEvolucao fonte={fonte} periodo={periodo} />
        </div>
        <div className={estilos.complementar}>
          <BlocoDeSituacaoDasEntregas fonte={fonte} periodo={periodo} />
        </div>
      </div>
      <BlocoDePedidosRecentes fonte={fonte} periodo={periodo} />
    </>
  );
}
