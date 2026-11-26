import { DataTable, type Coluna } from "../componentes/DataTable";
import { EmptyState } from "../componentes/EmptyState";
import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { StatusChip, type TomDaSituacao } from "../componentes/StatusChip";
import { formatarData } from "../formatacao";
import { MolduraDeTabela } from "../painel/MolduraDeTabela";
import type { Periodo } from "../painel/periodo";
import { useBloco, type FonteDeDados } from "../useBloco";
import estilos from "./BlocoDeLeadsRecentes.module.css";
import type { Etapa } from "./etapas";
import { eLeadsRecentes, LIMITE_DE_LEADS_RECENTES, type LeadRecente } from "./leadsRecentes";

interface Propriedades {
  fonte: FonteDeDados;
  periodo: Periodo;
}

/** Em negociação é informação; só o fim da negociação tem cor de resultado. */
const TOM_DA_ETAPA: Record<Etapa, TomDaSituacao> = {
  Novo: "neutro",
  Contatado: "informacao",
  Qualificado: "informacao",
  Proposta: "informacao",
  Fechado: "sucesso",
  Perdido: "erro",
};

const COLUNAS: Coluna<LeadRecente>[] = [
  { titulo: "Empresa", celula: (l) => l.empresa },
  { titulo: "Canal", celula: (l) => l.canal },
  { titulo: "Etapa", celula: (l) => <StatusChip texto={l.etapa} tom={TOM_DA_ETAPA[l.etapa]} /> },
  { titulo: "Criação", celula: (l) => formatarData(l.data_criacao) },
  {
    titulo: "Fechamento",
    celula: (l) =>
      l.data_fechamento === null ? (
        <>
          <span className={estilos.secundario} aria-hidden="true">
            —
          </span>
          <span className="visualmente-oculto">Sem fechamento</span>
        </>
      ) : (
        formatarData(l.data_fechamento)
      ),
  },
];

/** A tabela dos leads, já carregados. */
export function TabelaDeLeadsRecentes({ leads }: { leads: LeadRecente[] }) {
  return (
    <DataTable
      rotulo="Leads recentes do período"
      colunas={COLUNAS}
      linhas={leads}
      chave={(l) => l.lead}
    />
  );
}

const MOLDURA = {
  titulo: "Leads recentes",
  descricao:
    `Os ${LIMITE_DE_LEADS_RECENTES} leads mais recentes do período, do mais novo para o mais ` +
    "antigo pela data de criação. O fechamento fica vazio em quem não virou lojista.",
};

/** A tabela dos leads mais recentes do período, com estados próprios (FE §6, §7, §10). */
export function BlocoDeLeadsRecentes({ fonte, periodo }: Propriedades) {
  const { estado, tentarDeNovo } = useBloco(
    fonte,
    `/comercial/leads?periodo=${periodo}`,
    eLeadsRecentes,
  );

  return (
    <EstadosDoBloco
      estado={estado}
      tentarDeNovo={tentarDeNovo}
      nome="os leads recentes"
      carregando={
        <MolduraDeTabela {...MOLDURA} ocupado>
          <AnuncioDeCarregamento texto="Carregando os leads recentes…">
            <LoadingSkeleton forma="tabela" linhas={8} />
          </AnuncioDeCarregamento>
        </MolduraDeTabela>
      }
    >
      {(dados) =>
        dados.leads.length === 0 ? (
          <EmptyState
            titulo="Nenhum lead no período"
            descricao="Não há leads criados nestes dias. Escolha um período maior para ver os leads recentes."
          />
        ) : (
          <MolduraDeTabela {...MOLDURA}>
            <TabelaDeLeadsRecentes leads={dados.leads} />
          </MolduraDeTabela>
        )
      }
    </EstadosDoBloco>
  );
}
