import { useEffect, useEffectEvent, useId, useRef, type ReactNode } from "react";

import { IconeAviso, IconeCadeado, IconeCheck, IconeFechar } from "../componentes/icones";
import { formatarDataHora, formatarNumero } from "../formatacao";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import { ROTULO_DA_CAMADA, type Alvo, type CenarioExecutado, type Quem } from "./contrato";
import estilos from "./GavetaDoCenario.module.css";
import painel from "./PainelDeSeguranca.module.css";
import { abrirGaveta } from "./teclado";

const ROTULO_DE_QUEM: Record<Quem["tipo"], string> = {
  usuario: "Usuário",
  papel: "Papel do banco",
  token: "Token",
};

const ROTULO_DO_ALVO: Record<Alvo["tipo"], string> = {
  rota: "Rota da API",
  ferramenta: "Ferramenta",
  lista_de_ferramentas: "Lista de ferramentas",
  camada_de_leitura: "Camada de leitura",
  dados_de_origem: "Dados de origem",
  conversa: "Conversa",
  assistente: "Assistente",
};

function Item({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className={estilos.item}>
      <dt>{rotulo}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function parametrosPorExtenso(parametros: Record<string, unknown>): string {
  const pares = Object.entries(parametros);
  if (pares.length === 0) return "Nenhum";
  return pares
    .map(
      ([nome, valor]) => `${nome} = ${typeof valor === "string" ? valor : JSON.stringify(valor)}`,
    )
    .join(", ");
}

function Desfecho({ cenario }: { cenario: CenarioExecutado }) {
  const permitido = cenario.obtido === "permitido";
  return (
    <span className={painel.resultado}>
      <span className={painel.desfecho} data-desfecho={cenario.obtido}>
        {permitido ? <IconeCheck /> : <IconeCadeado />}
        {permitido ? "Permitido" : "Negado"}
      </span>
      {cenario.divergencia && (
        <span className={painel.divergencia}>
          <IconeAviso />
          Divergência: esperado {cenario.esperado}
        </span>
      )}
    </span>
  );
}

function Pedido({ cenario }: { cenario: CenarioExecutado }) {
  const { quem, perfil, alvo } = cenario;
  return (
    <section className={estilos.secao} aria-labelledby={`${cenario.id}-pedido`}>
      <h3 id={`${cenario.id}-pedido`} className={estilos.tituloDaSecao}>
        Pedido
      </h3>
      <dl className={estilos.lista}>
        <Item rotulo={ROTULO_DE_QUEM[quem.tipo]}>{quem.nome}</Item>
        <Item rotulo="Perfil">{perfil ? DESCRICAO_DOS_PERFIS[perfil].nome : "Sem perfil"}</Item>
        <Item rotulo={ROTULO_DO_ALVO[alvo.tipo]}>
          <code>{alvo.nome}</code>
        </Item>
        <Item rotulo="Parâmetros">{parametrosPorExtenso(alvo.parametros)}</Item>
      </dl>
    </section>
  );
}

function RespostaObtida({ cenario }: { cenario: CenarioExecutado }) {
  const { resposta, obtido } = cenario;
  return (
    <section className={estilos.secao} aria-labelledby={`${cenario.id}-resposta`}>
      <h3 id={`${cenario.id}-resposta`} className={estilos.tituloDaSecao}>
        Resposta
      </h3>
      <dl className={estilos.lista}>
        <Item rotulo="Resultado">
          <Desfecho cenario={cenario} />
        </Item>
        <Item rotulo="Status">{resposta.status ?? "Sem status"}</Item>
        {obtido === "permitido" ? (
          resposta.linhas !== null && (
            <Item rotulo="Linhas">
              {resposta.linhas === 1 ? "1 linha" : `${formatarNumero(resposta.linhas)} linhas`}
            </Item>
          )
        ) : (
          <Item rotulo="Mensagem">{resposta.mensagem ?? "Sem mensagem no corpo"}</Item>
        )}
      </dl>
    </section>
  );
}

function CamadasDeDefesa({ cenario }: { cenario: CenarioExecutado }) {
  const barrado = cenario.obtido === "negado";
  return (
    <section className={estilos.secao} aria-labelledby={`${cenario.id}-camadas`}>
      <h3 id={`${cenario.id}-camadas`} className={estilos.tituloDaSecao}>
        Camadas de defesa
      </h3>
      <p className={estilos.nota}>
        {barrado ? "Barrado por:" : "Nenhuma camada barrou: o pedido atravessou as camadas abaixo."}
      </p>
      <ul className={estilos.camadas} aria-label="Camadas de defesa">
        {cenario.camadas_de_defesa.map((camada) => (
          <li key={camada} className={estilos.camada} data-barrou={barrado || undefined}>
            {ROTULO_DA_CAMADA[camada]}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Auditoria({ cenario }: { cenario: CenarioExecutado }) {
  const { auditoria } = cenario;
  return (
    <section className={estilos.secao} aria-labelledby={`${cenario.id}-auditoria`}>
      <h3 id={`${cenario.id}-auditoria`} className={estilos.tituloDaSecao}>
        Auditoria
      </h3>
      {auditoria ? (
        <dl className={estilos.lista}>
          <Item rotulo="Linha">#{auditoria.id}</Item>
          <Item rotulo="Horário">
            <time dateTime={auditoria.horario}>{formatarDataHora(auditoria.horario)}</time>
          </Item>
          <Item rotulo="Usuário">{auditoria.usuario}</Item>
          <Item rotulo="Ferramenta">
            <code>{auditoria.ferramenta}</code>
          </Item>
          <Item rotulo="Argumentos">{parametrosPorExtenso(auditoria.argumentos ?? {})}</Item>
          <Item rotulo="Desfecho">{auditoria.resultado}</Item>
        </dl>
      ) : (
        <p className={estilos.nota}>
          Sem linha na auditoria: só as chamadas de ferramenta ficam registradas nela.
        </p>
      )}
    </section>
  );
}

interface Propriedades {
  cenario: CenarioExecutado;
  aoFechar: () => void;
  /** A linha que abriu a gaveta: recebe o foco de volta ao fechar. */
  origem?: HTMLElement | null;
}

/**
 * A gaveta lateral com o detalhe de um cenário (FE §9): o pedido, a resposta, as camadas de
 * defesa, a linha da auditoria e a duração. Nada de token, segredo ou dado de negócio: um
 * permitido traz só o status e a quantidade de linhas. Recebe o foco ao abrir, fecha com Esc e
 * devolve o foco à linha.
 */
export function GavetaDoCenario({ cenario, aoFechar, origem = null }: Propriedades) {
  const idDoTitulo = useId();
  const gaveta = useRef<HTMLElement>(null);
  const fechar = useEffectEvent(aoFechar);

  useEffect(() => {
    if (!gaveta.current) return;
    return abrirGaveta(window, gaveta.current, origem, () => fechar());
  }, [cenario.id, origem]);

  return (
    <aside
      ref={gaveta}
      className={estilos.gaveta}
      role="dialog"
      aria-labelledby={idDoTitulo}
      tabIndex={-1}
    >
      <header className={estilos.cabecalho}>
        <div className={estilos.titulos}>
          <p className={estilos.contexto}>Cenário de segurança</p>
          <h2 id={idDoTitulo} className={estilos.titulo}>
            {cenario.descricao}
          </h2>
        </div>
        <button
          type="button"
          className={estilos.fechar}
          onClick={aoFechar}
          aria-label="Fechar o detalhe do cenário"
          aria-keyshortcuts="Escape"
        >
          <IconeFechar />
        </button>
      </header>
      <div className={estilos.corpo}>
        <Pedido cenario={cenario} />
        <RespostaObtida cenario={cenario} />
        <CamadasDeDefesa cenario={cenario} />
        <Auditoria cenario={cenario} />
        <p className={estilos.duracao}>
          Duração: <strong>{formatarNumero(cenario.duracao_em_ms)} ms</strong>
        </p>
      </div>
    </aside>
  );
}
