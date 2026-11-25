import { DataTable, type Coluna } from "../componentes/DataTable";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { StatusChip, type TomDaSituacao } from "../componentes/StatusChip";
import { formatarDataHora, formatarMoeda } from "../formatacao";
import { MolduraDeTabela } from "../painel/MolduraDeTabela";
import type { Periodo } from "../painel/periodo";
import { useBloco, type FonteDeDados } from "../useBloco";
import estilos from "./BlocoDePedidosRecentes.module.css";
import {
  ePedidosRecentes,
  LIMITE_DE_PEDIDOS_RECENTES,
  type PedidoRecente,
  type SituacaoDeEntrega,
  type SituacaoDePagamento,
} from "./pedidosRecentes";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

const TOM_DO_PAGAMENTO: Record<SituacaoDePagamento, TomDaSituacao> = {
  Aprovado: "sucesso",
  Recusado: "erro",
};

const TOM_DA_ENTREGA: Record<SituacaoDeEntrega, TomDaSituacao> = {
  "Em trânsito": "informacao",
  "Prazo vencido": "atencao",
  "Entregue no prazo": "sucesso",
  "Entregue com atraso": "erro",
};

const COLUNAS: Coluna<PedidoRecente>[] = [
  { titulo: "Pedido", celula: (p) => <span className={estilos.numero}>#{p.numero}</span> },
  { titulo: "Compra", celula: (p) => formatarDataHora(p.momento_compra) },
  {
    titulo: "Cidade do cliente",
    celula: (p) => (
      <>
        {p.cidade} <span className={estilos.secundario}>{p.uf}</span>
      </>
    ),
  },
  { titulo: "Lojista", celula: (p) => p.lojista },
  { titulo: "Rota", celula: (p) => p.rota },
  { titulo: "Valor", alinhamento: "fim", celula: (p) => formatarMoeda(p.valor) },
  {
    titulo: "Pagamento",
    celula: (p) => <StatusChip texto={p.pagamento} tom={TOM_DO_PAGAMENTO[p.pagamento]} />,
  },
  {
    titulo: "Entrega",
    celula: (p) =>
      p.entrega === null ? (
        <>
          <span className={estilos.secundario} aria-hidden="true">
            —
          </span>
          <span className="visualmente-oculto">Sem entrega</span>
        </>
      ) : (
        <StatusChip texto={p.entrega} tom={TOM_DA_ENTREGA[p.entrega]} />
      ),
  },
];

const MOLDURA = {
  titulo: "Pedidos recentes",
  descricao:
    `Os ${LIMITE_DE_PEDIDOS_RECENTES} pedidos mais recentes do período, do mais novo para o ` +
    "mais antigo. Horários de Brasília.",
};

/** A tabela dos pedidos mais recentes do período, com estados próprios (FE §6, §7, §10). */
export function BlocoDePedidosRecentes({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/vendas/pedidos-recentes?periodo=${periodo}`,
    ePedidosRecentes,
  );

  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="os pedidos recentes"
      carregando={
        <MolduraDeTabela {...MOLDURA} ocupado>
          <AnuncioDeCarregamento texto="Carregando os pedidos recentes…">
            <LoadingSkeleton forma="tabela" linhas={8} />
          </AnuncioDeCarregamento>
        </MolduraDeTabela>
      }
    >
      {(dados) =>
        dados.pedidos.length === 0 ? (
          <EmptyState
            titulo="Nenhum pedido no período"
            descricao="Não há pedidos realizados nestes dias. Escolha um período maior para ver os pedidos recentes."
          />
        ) : (
          <MolduraDeTabela {...MOLDURA}>
            <DataTable
              rotulo="Pedidos recentes do período"
              colunas={COLUNAS}
              linhas={dados.pedidos}
              chave={(p) => p.numero}
            />
          </MolduraDeTabela>
        )
      }
    </EstadosDoBloco>
  );
}
