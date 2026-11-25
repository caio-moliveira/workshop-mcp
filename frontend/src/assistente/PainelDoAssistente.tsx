import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import type { UsuarioAutenticado } from "../api";
import { IconeAssistente, IconeAviso, IconeEnviar, IconeFechar } from "../componentes/icones";
import { DESCRICAO_DOS_PERFIS } from "../perfis";
import { podeEnviar, type Conversa, type RespostaDoAssistente } from "./conversa";
import estilos from "./PainelDoAssistente.module.css";

interface Propriedades {
  usuario: UsuarioAutenticado;
  conversa: Conversa;
  aoPerguntar: (pergunta: string) => void;
  aoFechar: () => void;
}

const LINHAS_DO_CAMPO = 5;

/** O chat lateral do assistente, à direita e por cima do conteúdo (FE §8). */
export function PainelDoAssistente({ usuario, conversa, aoPerguntar, aoFechar }: Propriedades) {
  const perfil = DESCRICAO_DOS_PERFIS[usuario.perfil];
  const [pergunta, setPergunta] = useState("");
  const campo = useRef<HTMLTextAreaElement>(null);
  const fim = useRef<HTMLDivElement>(null);
  const envioLiberado = podeEnviar(conversa, pergunta);

  useEffect(() => {
    campo.current?.focus();
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

  // A conversa acompanha o texto que chega.
  useEffect(() => {
    fim.current?.scrollIntoView({ block: "end" });
  }, [conversa]);

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

  return (
    <aside id="assistente" className={estilos.painel} aria-labelledby="titulo-do-assistente">
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
          onClick={aoFechar}
          aria-label="Fechar o assistente"
        >
          <IconeFechar />
        </button>
      </header>

      <div className={estilos.conversa} role="log" aria-label="Conversa com o assistente">
        {conversa.falas.length === 0 && (
          <div className={estilos.inicio}>
            <p>Pergunte em linguagem natural sobre os dados do seu perfil.</p>
            {perfil.perguntaSugerida && (
              <button
                type="button"
                className={estilos.sugestao}
                onClick={() => enviarPergunta(perfil.perguntaSugerida ?? "")}
              >
                {perfil.perguntaSugerida}
              </button>
            )}
          </div>
        )}
        {conversa.falas.map((fala, indice) =>
          fala.autor === "usuario" ? (
            <p key={indice} className={estilos.pergunta}>
              {fala.texto}
            </p>
          ) : (
            <Resposta key={indice} resposta={fala} />
          ),
        )}
        <div ref={fim} />
      </div>

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
        />
        <button
          type="submit"
          className={estilos.enviar}
          disabled={!envioLiberado}
          aria-label="Enviar pergunta"
        >
          <IconeEnviar />
        </button>
      </form>
    </aside>
  );
}

function Resposta({ resposta }: { resposta: RespostaDoAssistente }) {
  return (
    <div className={estilos.resposta} aria-busy={resposta.situacao === "chegando"}>
      {resposta.texto && <p className={estilos.textoDaResposta}>{resposta.texto}</p>}
      {resposta.consultando && (
        <p className={estilos.status}>
          <span className={estilos.atividade} aria-hidden="true" />
          Consultando os dados…
        </p>
      )}
      {resposta.situacao === "erro" && (
        <p className={estilos.erro}>
          <IconeAviso />
          {resposta.erro}
        </p>
      )}
    </div>
  );
}
