/**
 * O bloco retrátil "Como esta resposta foi obtida" (FE §8, `ToolTraceDisclosure`): as chamadas que
 * produziram a resposta, com a ferramenta pedida, o desfecho e a duração, e o identificador da
 * pergunta, que o apresentador procura nos logs.
 *
 * Fechado por padrão, para não competir com a resposta. O botão anuncia aos leitores de tela se o
 * bloco está aberto (`aria-expanded`). Nada aqui mostra parâmetros nem texto de erro: o rastreio
 * não os tem.
 */
import { useId, useState } from "react";

import type { ChamadaDoRastreio } from "./fluxo";
import estilos from "./RastreioDaResposta.module.css";

const DESFECHO: Record<ChamadaDoRastreio["desfecho"], string> = {
  concluida: "concluída",
  nao_concluida: "não concluída",
};

const milissegundos = new Intl.NumberFormat("pt-BR");

/**
 * A chave de uma chamada na lista. O contrato não dá identificador à chamada, e a mesma ferramenta
 * pode ser chamada duas vezes com o mesmo desfecho: a posição completa o conteúdo. O rastreio só
 * cresce no fim, então a posição de uma chamada não muda.
 */
function chaveDaChamada(chamada: ChamadaDoRastreio, posicao: number): string {
  return `${posicao}:${chamada.ferramenta}:${chamada.desfecho}:${chamada.milissegundos}`;
}

interface Propriedades {
  rastreio: readonly ChamadaDoRastreio[];
  idDaPergunta?: string;
}

export function RastreioDaResposta({ rastreio, idDaPergunta }: Propriedades) {
  const [aberto, setAberto] = useState(false);
  const conteudo = useId();
  return (
    <div className={estilos.rastreio}>
      <button
        type="button"
        className={estilos.alternar}
        aria-expanded={aberto}
        aria-controls={conteudo}
        onClick={() => setAberto((atual) => !atual)}
      >
        <span className={estilos.seta} aria-hidden="true">
          {aberto ? "▾" : "▸"}
        </span>
        Como esta resposta foi obtida
      </button>
      <div id={conteudo} className={estilos.conteudo} hidden={!aberto}>
        {rastreio.length === 0 ? (
          <p className={estilos.vazio}>Nenhuma ferramenta foi consultada.</p>
        ) : (
          <ol className={estilos.chamadas}>
            {rastreio.map((chamada, posicao) => (
              <li key={chaveDaChamada(chamada, posicao)} className={estilos.chamada}>
                <code className={estilos.ferramenta}>{chamada.ferramenta}</code>
                <span className={estilos[chamada.desfecho]}>{DESFECHO[chamada.desfecho]}</span>
                <span className={estilos.duracao}>
                  {milissegundos.format(chamada.milissegundos)} ms
                </span>
              </li>
            ))}
          </ol>
        )}
        {idDaPergunta && (
          <p className={estilos.pergunta}>
            Pergunta <code>{idDaPergunta}</code>
          </p>
        )}
      </div>
    </div>
  );
}
