import { AnuncioDeCarregamento } from "../componentes/EstadosDoBloco";
import { EmptyState } from "../componentes/EmptyState";
import { IconeAviso, IconeCadeado, IconeCheck } from "../componentes/icones";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { formatarHora } from "../formatacao";
import { MolduraDeTabela } from "../painel/MolduraDeTabela";
import type { FonteDeDados } from "../useBloco";
import { useChamadasAoVivo, type EstadoDasChamadasAoVivo } from "./aoVivo";
import estilos from "./ChamadasAoVivo.module.css";
import type { ChamadaAoVivo, ResultadoDaAuditoria } from "./contrato";
import painel from "./PainelDeSeguranca.module.css";
import { nomeDoPerfil } from "./porExtenso";

const MOLDURA = {
  titulo: "Chamadas ao vivo",
  descricao:
    "As últimas chamadas ao servidor MCP, de qualquer usuário e assistente, como ficam na auditoria. Atualiza a cada 3 segundos.",
};

const ROTULO_DO_RESULTADO: Record<ResultadoDaAuditoria, string> = {
  permitida: "Permitida",
  negada: "Negada",
  limitada: "Barrada pelo limite",
  parametro_invalido: "Parâmetro inválido",
  falha: "Falha",
};

/** O desfecho com ícone e texto, nunca só a cor (FE §9). */
function Desfecho({ resultado }: { resultado: ResultadoDaAuditoria }) {
  const barrada = resultado === "negada" || resultado === "limitada";
  return (
    <span className={estilos.desfecho} data-resultado={resultado}>
      {resultado === "permitida" ? <IconeCheck /> : barrada ? <IconeCadeado /> : <IconeAviso />}
      {ROTULO_DO_RESULTADO[resultado]}
    </span>
  );
}

function TabelaDasChamadas({ chamadas }: { chamadas: ChamadaAoVivo[] }) {
  return (
    <div className={painel.rolagem} role="region" aria-label="Chamadas ao vivo" tabIndex={0}>
      <table className={`${painel.tabela} ${estilos.tabela}`}>
        <caption className="visualmente-oculto">Chamadas ao vivo</caption>
        <thead>
          <tr>
            <th scope="col">Horário</th>
            <th scope="col">Quem chamou</th>
            <th scope="col">Ferramenta</th>
            <th scope="col">Desfecho</th>
          </tr>
        </thead>
        <tbody>
          {chamadas.map((chamada, posicao) => (
            <tr
              key={`${chamada.horario} ${chamada.usuario} ${chamada.ferramenta} ${posicao}`}
              data-resultado={chamada.resultado}
            >
              <td>
                <time dateTime={chamada.horario} className={estilos.horario}>
                  {formatarHora(chamada.horario)}
                </time>
              </td>
              <td>
                <span className={painel.empilhado}>
                  <span>{chamada.usuario}</span>
                  <span className={painel.secundario}>{nomeDoPerfil(chamada.perfil)}</span>
                </span>
              </td>
              <td className={estilos.ferramenta}>{chamada.ferramenta}</td>
              <td>
                <Desfecho resultado={chamada.resultado} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** O bloco das chamadas ao vivo, pelo estado dado. */
export function VisaoDasChamadasAoVivo({ estado }: { estado: EstadoDasChamadasAoVivo }) {
  switch (estado.fase) {
    case "carregando":
      return (
        <MolduraDeTabela {...MOLDURA} ocupado>
          <AnuncioDeCarregamento texto="Carregando as chamadas ao vivo…">
            <LoadingSkeleton forma="tabela" linhas={3} />
          </AnuncioDeCarregamento>
        </MolduraDeTabela>
      );
    case "erro":
      return (
        <MolduraDeTabela {...MOLDURA}>
          <p className={estilos.aviso} role="status">
            <IconeAviso />A auditoria não respondeu. A lista aparece assim que ela responder.
          </p>
        </MolduraDeTabela>
      );
    case "pronto":
      return (
        <MolduraDeTabela {...MOLDURA}>
          {estado.atrasado && (
            <p className={estilos.aviso} role="status">
              <IconeAviso />
              Sem atualização: a auditoria não respondeu na última tentativa.
            </p>
          )}
          {estado.chamadas.length === 0 ? (
            <EmptyState
              titulo="Nenhuma chamada ainda"
              descricao="Faça uma pergunta no assistente do pulso., no Claude ou no ChatGPT: cada chamada ao servidor MCP aparece aqui."
            />
          ) : (
            <TabelaDasChamadas chamadas={estado.chamadas} />
          )}
        </MolduraDeTabela>
      );
  }
}

/** As chamadas ao vivo buscando `GET /seguranca/chamadas` a cada 3 segundos. */
export function ChamadasAoVivo({ fonte }: { fonte: FonteDeDados }) {
  return <VisaoDasChamadasAoVivo estado={useChamadasAoVivo(fonte)} />;
}
