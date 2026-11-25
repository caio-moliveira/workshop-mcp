import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type RefObject,
} from "react";

import type { UsuarioAutenticado } from "../api";
import { ErrorState } from "../componentes/ErrorState";
import {
  IconeAssistente,
  IconeAviso,
  IconeConversas,
  IconeEnviar,
  IconeExpandir,
  IconeFechar,
  IconeNovaConversa,
  IconeParar,
  IconeRecolher,
} from "../componentes/icones";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import { podeEnviar, respondendo, type Conversa, type RespostaDoAssistente } from "./conversa";
import { caracteresDaPergunta, LIMITE_DE_CARACTERES_DA_PERGUNTA, passouDoLimite } from "./limites";
import { VisaoDasConversas } from "./VisaoDasConversas";
import estilos from "./PainelDoAssistente.module.css";
import { RastreioDaResposta } from "./RastreioDaResposta";
import { TextoEmMarkdown } from "./TextoEmMarkdown";
import type { Abertura, FonteDoAssistente } from "./useConversa";

interface Propriedades {
  usuario: UsuarioAutenticado;
  /** De onde vem a lista de conversas do histórico. */
  fonte: FonteDoAssistente;
  conversa: Conversa;
  abertura: Abertura;
  /** O modo expandido: a área de leitura com a lista de conversas ao lado (FE §8). */
  expandido: boolean;
  /** Ausente abaixo de 768 px: ali o painel já ocupa a tela, e não há o que expandir. */
  aoAlternarExpansao?: () => void;
  aoPerguntar: (pergunta: string) => void;
  aoParar: () => void;
  aoAbrir: (id: string) => void;
  aoComecarNova: () => void;
  aoFechar: () => void;
}

const LINHAS_DO_CAMPO = 5;

/**
 * O assistente, em duas formas do mesmo painel (FE §8), com a mesma conversa: o chat lateral, à
 * direita e por cima do conteúdo, em que a visão "Conversas" troca a conversa pela lista do
 * histórico; e o modo expandido, uma área de leitura com a lista sempre numa coluna à esquerda.
 * As duas formas são o mesmo componente na mesma posição da árvore: alternar entre elas não perde
 * a pergunta em digitação, nem a resposta que está chegando.
 */
export function PainelDoAssistente({
  usuario,
  fonte,
  conversa,
  abertura,
  expandido,
  aoAlternarExpansao,
  aoPerguntar,
  aoParar,
  aoAbrir,
  aoComecarNova,
  aoFechar,
}: Propriedades) {
  const perfil = DESCRICAO_DOS_PERFIS[usuario.perfil];
  const [visao, setVisao] = useState<"conversa" | "conversas">("conversa");
  const [pergunta, setPergunta] = useState("");
  const campo = useRef<HTMLTextAreaElement>(null);
  const fim = useRef<HTMLDivElement>(null);
  const envioLiberado = podeEnviar(conversa, pergunta);
  const longaDemais = passouDoLimite(pergunta);
  // No modo expandido a lista já está ao lado: a conversa fica sempre na coluna central.
  const mostraALista = !expandido && visao === "conversas";

  // Ao abrir, o foco vai ao campo; ao fechar (botão ou Esc), volta a quem abriu o painel.
  useEffect(() => {
    const anterior = document.activeElement;
    campo.current?.focus();
    return () => {
      if (anterior instanceof HTMLElement && anterior.isConnected) anterior.focus();
    };
  }, []);

  // O campo cresce com o texto, de 1 a 5 linhas; depois disso rola.
  useLayoutEffect(() => {
    const elemento = campo.current;
    if (!elemento) return;
    const { lineHeight, paddingTop, paddingBottom } = getComputedStyle(elemento);
    const maximo =
      parseFloat(lineHeight) * LINHAS_DO_CAMPO + parseFloat(paddingTop) + parseFloat(paddingBottom);
    elemento.style.height = "auto";
    elemento.style.height = `${Math.min(elemento.scrollHeight, maximo)}px`;
  }, [pergunta]);

  // A conversa acompanha o texto que chega, e volta ao fim ao sair da lista ou trocar de modo.
  useEffect(() => {
    fim.current?.scrollIntoView({ block: "end" });
  }, [conversa, mostraALista, expandido]);

  // De volta à conversa (nova ou reaberta), o foco vai ao campo da pergunta.
  useEffect(() => {
    if (!mostraALista && abertura.situacao === "pronta") campo.current?.focus();
  }, [mostraALista, abertura.situacao]);

  function comecarNova() {
    aoComecarNova();
    setPergunta("");
    setVisao("conversa");
  }

  function abrir(id: string) {
    aoAbrir(id);
    setVisao("conversa");
  }

  function enviarPergunta(texto: string) {
    if (!podeEnviar(conversa, texto)) return;
    aoPerguntar(texto.trim());
    setPergunta("");
  }

  function aoSubmeter(evento: FormEvent) {
    evento.preventDefault();
    enviarPergunta(pergunta);
  }

  function aoTeclar(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (evento.key !== "Enter" || evento.shiftKey || evento.nativeEvent.isComposing) return;
    evento.preventDefault();
    enviarPergunta(pergunta);
  }

  const listaDeConversas = (
    <VisaoDasConversas
      fonte={fonte}
      idAtual={conversa.id}
      respondendo={respondendo(conversa)}
      aoAbrir={abrir}
      aoApagarAAtual={aoComecarNova}
    />
  );

  return (
    <aside
      id="assistente"
      className={expandido ? `${estilos.painel} ${estilos.expandido}` : estilos.painel}
      aria-labelledby="titulo-do-assistente"
    >
      <header className={estilos.cabecalho}>
        <span className={estilos.icone}>
          <IconeAssistente />
        </span>
        <div className={estilos.titulos}>
          <h2 id="titulo-do-assistente" className={estilos.titulo}>
            Assistente PULSO
          </h2>
          <p className={estilos.contexto}>Perfil {perfil.nome}</p>
        </div>
        <button
          type="button"
          className={estilos.fechar}
          onClick={comecarNova}
          aria-label="Nova conversa"
          title="Nova conversa"
        >
          <IconeNovaConversa />
        </button>
        {!expandido && (
          <button
            type="button"
            className={estilos.fechar}
            onClick={() => setVisao((atual) => (atual === "conversas" ? "conversa" : "conversas"))}
            aria-label="Conversas"
            aria-pressed={visao === "conversas"}
            title="Conversas"
          >
            <IconeConversas />
          </button>
        )}
        {aoAlternarExpansao && (
          <button
            type="button"
            className={estilos.fechar}
            onClick={aoAlternarExpansao}
            aria-label={expandido ? "Recolher o assistente" : "Expandir o assistente"}
            aria-keyshortcuts={expandido ? "Escape" : undefined}
            title={expandido ? "Recolher (Esc)" : "Expandir"}
          >
            {expandido ? <IconeRecolher /> : <IconeExpandir />}
          </button>
        )}
        <button
          type="button"
          className={estilos.fechar}
          onClick={aoFechar}
          aria-label="Fechar o assistente"
        >
          <IconeFechar />
        </button>
      </header>

      <div className={estilos.corpo}>
        {expandido && (
          <nav className={estilos.colunaDasConversas} aria-labelledby="titulo-das-conversas">
            <h3 id="titulo-das-conversas" className={estilos.tituloDaColuna}>
              Conversas
            </h3>
            {listaDeConversas}
          </nav>
        )}
        <div className={estilos.leitura}>
          {mostraALista ? (
            <div className={estilos.conversa}>
              <h3 className="visualmente-oculto">Conversas</h3>
              {listaDeConversas}
            </div>
          ) : abertura.situacao === "abrindo" ? (
            <div className={estilos.conversa} role="status" aria-live="polite">
              <p className={estilos.status}>
                <span className={estilos.atividade} aria-hidden="true" />
                Abrindo a conversa…
              </p>
            </div>
          ) : abertura.situacao === "erro" ? (
            <div className={estilos.conversa}>
              <ErrorState
                variante="bloco"
                titulo="Não foi possível abrir a conversa"
                descricao="Ela pode ter sido apagada em outra aba, ou o serviço está fora do ar."
                acao="Tentar de novo"
                aoAcionar={() => aoAbrir(abertura.id)}
              />
            </div>
          ) : (
            <ConversaNaTela
              conversa={conversa}
              expandido={expandido}
              nomeDoPerfil={perfil.nome}
              perguntaSugerida={perfil.perguntaSugerida}
              aoSugerir={enviarPergunta}
              fim={fim}
            />
          )}

          {/* A pergunta só vai para a conversa na tela: nem na lista, nem durante a abertura. */}
          {!mostraALista && abertura.situacao === "pronta" && (
            <form className={estilos.composer} onSubmit={aoSubmeter}>
              <label htmlFor="pergunta-ao-assistente" className="visualmente-oculto">
                Sua pergunta
              </label>
              <textarea
                id="pergunta-ao-assistente"
                ref={campo}
                className={estilos.campo}
                rows={1}
                value={pergunta}
                placeholder="Escreva sua pergunta"
                onChange={(evento) => setPergunta(evento.target.value)}
                onKeyDown={aoTeclar}
                aria-invalid={longaDemais}
                aria-describedby={longaDemais ? "pergunta-longa-demais" : undefined}
              />
              {/* Enquanto a resposta chega, o botão de enviar dá lugar ao de parar. */}
              {respondendo(conversa) ? (
                <button
                  type="button"
                  className={estilos.enviar}
                  onClick={aoParar}
                  aria-label="Parar a resposta"
                >
                  <IconeParar />
                </button>
              ) : (
                <button
                  type="submit"
                  className={estilos.enviar}
                  disabled={!envioLiberado}
                  aria-label="Enviar pergunta"
                >
                  <IconeEnviar />
                </button>
              )}
              {longaDemais && (
                <p className={estilos.limite}>
                  {/* Texto fixo no alerta: o leitor de tela anuncia uma vez, não a cada tecla. */}
                  <span id="pergunta-longa-demais" role="alert">
                    A pergunta passou do limite de{" "}
                    {LIMITE_DE_CARACTERES_DA_PERGUNTA.toLocaleString("pt-BR")} caracteres. Encurte
                    para enviar.
                  </span>
                  <span className={estilos.contagem} aria-hidden="true">
                    {caracteresDaPergunta(pergunta).toLocaleString("pt-BR")}/
                    {LIMITE_DE_CARACTERES_DA_PERGUNTA.toLocaleString("pt-BR")}
                  </span>
                </p>
              )}
            </form>
          )}
        </div>
      </div>
    </aside>
  );
}

interface PropriedadesDaConversa {
  conversa: Conversa;
  expandido: boolean;
  nomeDoPerfil: string;
  perguntaSugerida?: string;
  aoSugerir: (pergunta: string) => void;
  fim: RefObject<HTMLDivElement | null>;
}

/**
 * As perguntas e respostas da conversa atual; vazia, o convite e a pergunta sugerida. No modo
 * expandido o convite é editorial, com as sugestões em linhas, não em cartões (FE §8).
 */
function ConversaNaTela({
  conversa,
  expandido,
  nomeDoPerfil,
  perguntaSugerida,
  aoSugerir,
  fim,
}: PropriedadesDaConversa) {
  const vazia = conversa.perguntasERespostas.length === 0;
  return (
    <div className={estilos.conversa} role="log" aria-label="Conversa com o assistente">
      {vazia && expandido && (
        <div className={estilos.abertura}>
          <h3 className={estilos.manchete}>O que você quer saber sobre {nomeDoPerfil}?</h3>
          <p className={estilos.convite}>
            Pergunte em linguagem natural. O assistente responde só com os dados que o seu perfil
            alcança e mostra como chegou a cada resposta.
          </p>
          {perguntaSugerida && (
            <ul className={estilos.sugestoes} aria-label="Sugestões">
              <li>
                <button
                  type="button"
                  className={estilos.linhaDeSugestao}
                  onClick={() => aoSugerir(perguntaSugerida)}
                >
                  {perguntaSugerida}
                </button>
              </li>
            </ul>
          )}
        </div>
      )}
      {vazia && !expandido && (
        <div className={estilos.inicio}>
          <p>Pergunte em linguagem natural sobre os dados do seu perfil.</p>
          {perguntaSugerida && (
            <button
              type="button"
              className={estilos.sugestao}
              onClick={() => aoSugerir(perguntaSugerida)}
            >
              {perguntaSugerida}
            </button>
          )}
        </div>
      )}
      {conversa.perguntasERespostas.map((item, indice) =>
        item.autor === "usuario" ? (
          <p key={indice} className={estilos.pergunta}>
            {item.texto}
          </p>
        ) : (
          <Resposta key={indice} resposta={item} />
        ),
      )}
      <div ref={fim} />
    </div>
  );
}

function Resposta({ resposta }: { resposta: RespostaDoAssistente }) {
  return (
    <div className={estilos.resposta} aria-busy={resposta.situacao === "chegando"}>
      {resposta.texto && <TextoEmMarkdown texto={resposta.texto} />}
      {resposta.consultando && (
        <p className={estilos.status}>
          <span className={estilos.atividade} aria-hidden="true" />
          Consultando os dados…
        </p>
      )}
      {/* Antes do primeiro trecho, sem consulta: o indicador diz que a resposta está a caminho. */}
      {resposta.situacao === "chegando" && !resposta.consultando && !resposta.texto && (
        <p className={estilos.status}>
          <span className={estilos.atividade} aria-hidden="true" />
          Preparando a resposta…
        </p>
      )}
      {resposta.situacao === "interrompida" && (
        <p className={estilos.status}>Resposta interrompida.</p>
      )}
      {resposta.situacao === "erro" && (
        <p className={estilos.erro}>
          <IconeAviso />
          {resposta.erro}
        </p>
      )}
      {resposta.aviso && (
        <p className={estilos.aviso}>
          <IconeAviso />
          {resposta.aviso}
        </p>
      )}
      {/* Só depois de terminada: antes disso o rastreio ainda está incompleto. */}
      {resposta.situacao !== "chegando" && (
        <RastreioDaResposta rastreio={resposta.rastreio} idDaPergunta={resposta.idDaPergunta} />
      )}
    </div>
  );
}
