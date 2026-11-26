import { AnuncioDeCarregamento, EstadosDoBloco } from "../componentes/EstadosDoBloco";
import { EmptyState } from "../componentes/EmptyState";
import { IconeAviso, IconeCadeado, IconeCheck } from "../componentes/icones";
import { KpiCard } from "../componentes/KpiCard";
import { LoadingSkeleton } from "../componentes/LoadingSkeleton";
import { PageHeading } from "../componentes/PageHeading";
import { formatarDataHora, formatarNumero } from "../formatacao";
import grade from "../painel/GradeDeIndicadores.module.css";
import { MolduraDeTabela } from "../painel/MolduraDeTabela";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import { useBloco, type EstadoDoBloco, type FonteDeDados } from "../useBloco";
import {
  agruparPorCamada,
  ePainelDeSeguranca,
  ROTULO_DA_CAMADA,
  type CenarioExecutado,
  type ExecucaoDeAceite,
  type MatrizCompleta,
  type PainelDeSeguranca as Painel,
} from "./contrato";
import estilos from "./PainelDeSeguranca.module.css";

/** O comando que grava a execução de aceite, rodado dentro de `backend/`. */
export const COMANDO_DA_EXECUCAO_DE_ACEITE = "uv run python tests/execucao_de_aceite.py";

const MOLDURA = {
  titulo: "Cenários de segurança",
  descricao:
    "Cada pedido, quem o fez e o resultado, agrupados pela camada de defesa que o barra. Um permitido mostra só o status e a quantidade de linhas.",
};

function Cartoes({ execucao }: { execucao: ExecucaoDeAceite }) {
  const { executados, permitidos, negados, divergencias } = execucao.resumo;
  return (
    <div className={grade.grade}>
      <KpiCard
        rotulo="Executados"
        valor={formatarNumero(executados)}
        legenda="Cenários de segurança nesta execução"
      />
      <KpiCard
        rotulo="Permitidos"
        valor={formatarNumero(permitidos)}
        legenda="Pedidos que chegaram aos dados"
      />
      <KpiCard
        rotulo="Negados"
        valor={formatarNumero(negados)}
        legenda="Pedidos barrados por uma camada de defesa"
      />
      <KpiCard
        rotulo="Divergências"
        valor={formatarNumero(divergencias)}
        legenda={
          divergencias === 0
            ? "Todos os resultados como o esperado"
            : "Resultados diferentes do esperado"
        }
        destaque={divergencias > 0}
      />
    </div>
  );
}

function CartoesDaMatrizCompleta({ matriz }: { matriz: MatrizCompleta }) {
  return (
    <section className={estilos.secao} aria-labelledby="matriz-completa">
      <h2 id="matriz-completa" className={estilos.tituloDaSecao}>
        Matriz completa{" "}
        <span className={estilos.dataDaSecao}>
          de <time dateTime={matriz.executada_em}>{formatarDataHora(matriz.executada_em)}</time>
        </span>
      </h2>
      <div className={grade.grade}>
        <KpiCard
          rotulo="Pares executados"
          valor={formatarNumero(matriz.pares)}
          legenda="Rotas e ferramentas contra os quatro perfis"
        />
        <KpiCard
          rotulo="Pares permitidos"
          valor={formatarNumero(matriz.permitidos)}
          legenda="Só o dono de cada rota e ferramenta"
        />
        <KpiCard
          rotulo="Pares negados"
          valor={formatarNumero(matriz.negados)}
          legenda="Todos os outros perfis"
        />
        <KpiCard
          rotulo="Divergências na matriz"
          valor={formatarNumero(matriz.divergencias)}
          legenda={
            matriz.divergencias === 0
              ? "Todos os pares como o esperado"
              : "Pares diferentes do esperado"
          }
          destaque={matriz.divergencias > 0}
        />
      </div>
    </section>
  );
}

/** O resultado com ícone e texto, nunca só a cor (FE §9). */
function Resultado({ cenario }: { cenario: CenarioExecutado }) {
  const permitido = cenario.obtido === "permitido";
  return (
    <span className={estilos.resultado}>
      <span className={estilos.desfecho} data-desfecho={cenario.obtido}>
        {permitido ? <IconeCheck /> : <IconeCadeado />}
        {permitido ? "Permitido" : "Negado"}
      </span>
      {cenario.divergencia && (
        <span className={estilos.divergencia}>
          <IconeAviso />
          Divergência: esperado {cenario.esperado}
        </span>
      )}
    </span>
  );
}

function linhasPorExtenso(linhas: number): string {
  return linhas === 1 ? "1 linha" : `${formatarNumero(linhas)} linhas`;
}

/** O status e, no negado, a mensagem genérica; no permitido, a quantidade de linhas. */
function detalhe({ resposta, obtido }: CenarioExecutado): string {
  const partes: string[] = [];
  if (resposta.status !== null) partes.push(String(resposta.status));
  if (obtido === "permitido" && resposta.linhas !== null) {
    partes.push(linhasPorExtenso(resposta.linhas));
  } else if (resposta.mensagem) {
    partes.push(resposta.mensagem);
  }
  return partes.join(" · ") || "—";
}

function Perfil({ cenario }: { cenario: CenarioExecutado }) {
  return (
    <span className={estilos.empilhado}>
      <span>{cenario.quem.nome}</span>
      <span className={estilos.secundario}>
        {cenario.perfil ? DESCRICAO_DOS_PERFIS[cenario.perfil].nome : "Sem perfil"}
      </span>
    </span>
  );
}

/** A matriz dos cenários, um grupo por camada de defesa, rolando dentro da moldura (FE §11). */
export function MatrizDeCenarios({ cenarios }: { cenarios: CenarioExecutado[] }) {
  return (
    <div
      className={estilos.rolagem}
      role="region"
      aria-label="Matriz dos cenários de segurança"
      tabIndex={0}
    >
      <table className={estilos.tabela}>
        <caption className="visualmente-oculto">Matriz dos cenários de segurança</caption>
        <thead>
          <tr>
            <th scope="col">Cenário</th>
            <th scope="col">Perfil</th>
            <th scope="col">Resultado</th>
            <th scope="col">Detalhes</th>
          </tr>
        </thead>
        {agruparPorCamada(cenarios).map(({ grupo, cenarios: doGrupo }) => (
          <tbody key={grupo}>
            <tr className={estilos.linhaDoGrupo}>
              <th scope="rowgroup" colSpan={4}>
                {ROTULO_DA_CAMADA[grupo]}
              </th>
            </tr>
            {doGrupo.map((cenario) => (
              <tr key={cenario.id} data-divergencia={cenario.divergencia || undefined}>
                <td>
                  <span className={estilos.empilhado}>
                    <span>{cenario.descricao}</span>
                    <span className={estilos.secundario}>{cenario.alvo.nome}</span>
                  </span>
                </td>
                <td>
                  <Perfil cenario={cenario} />
                </td>
                <td>
                  <Resultado cenario={cenario} />
                </td>
                <td>
                  <span className={estilos.empilhado}>
                    <span>{detalhe(cenario)}</span>
                    <span className={estilos.secundario}>{cenario.duracao_em_ms} ms</span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        ))}
      </table>
    </div>
  );
}

function Execucao({ execucao }: { execucao: ExecucaoDeAceite }) {
  return (
    <>
      <Cartoes execucao={execucao} />
      {execucao.matriz_completa && <CartoesDaMatrizCompleta matriz={execucao.matriz_completa} />}
      {execucao.carga && (
        <p className={estilos.carga} data-confere={execucao.carga.confere}>
          {execucao.carga.confere ? <IconeCheck /> : <IconeAviso />}
          {execucao.carga.confere
            ? "O banco está no estado da carga."
            : `O banco não está no estado da carga${execucao.carga.detalhe ? `: ${execucao.carga.detalhe}` : "."}`}
        </p>
      )}
      <MolduraDeTabela {...MOLDURA}>
        <MatrizDeCenarios cenarios={execucao.cenarios} />
      </MolduraDeTabela>
    </>
  );
}

interface Busca {
  estado: EstadoDoBloco<Painel>;
  tentarDeNovo: () => void;
}

/**
 * O painel de segurança (FE §9): a última execução de aceite, igual para os quatro perfis e sem
 * seletor de período. Nunca mostra token, segredo nem dado de negócio.
 */
export function VisaoDoPainelDeSeguranca({ estado, tentarDeNovo }: Busca) {
  const execucao = estado.fase === "pronto" ? estado.dados.execucao : null;
  return (
    <>
      <PageHeading
        contexto="Demonstração"
        titulo="Segurança"
        subtitulo="A última execução de aceite: cada cenário de segurança, permitido ou negado, e a camada de defesa que o barra."
        controles={
          execucao && (
            <p className={estilos.dataDaExecucao}>
              Execução de aceite de{" "}
              <time dateTime={execucao.executada_em}>
                {formatarDataHora(execucao.executada_em)}
              </time>
            </p>
          )
        }
      />
      <EstadosDoBloco
        estado={estado}
        tentarDeNovo={tentarDeNovo}
        nome="a execução de aceite"
        carregando={
          <AnuncioDeCarregamento texto="Carregando a execução de aceite…" className={estilos.pilha}>
            <div className={grade.grade}>
              <LoadingSkeleton forma="cartao" />
              <LoadingSkeleton forma="cartao" />
              <LoadingSkeleton forma="cartao" />
              <LoadingSkeleton forma="cartao" />
            </div>
            <MolduraDeTabela {...MOLDURA} ocupado>
              <LoadingSkeleton forma="tabela" linhas={6} />
            </MolduraDeTabela>
          </AnuncioDeCarregamento>
        }
      >
        {({ execucao }) =>
          execucao ? (
            <Execucao execucao={execucao} />
          ) : (
            <EmptyState
              titulo="Nenhuma execução de aceite ainda"
              descricao={`Rode no terminal, dentro de backend/, o comando ${COMANDO_DA_EXECUCAO_DE_ACEITE} e recarregue esta página.`}
            />
          )
        }
      </EstadosDoBloco>
    </>
  );
}

/** O painel de segurança buscando `GET /seguranca`. */
export function PainelDeSeguranca({ fonte }: { fonte: FonteDeDados }) {
  const busca = useBloco(fonte, "/seguranca", ePainelDeSeguranca);
  return <VisaoDoPainelDeSeguranca {...busca} />;
}
