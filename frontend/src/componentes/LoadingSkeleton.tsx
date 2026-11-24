import estilos from "./LoadingSkeleton.module.css";

interface Propriedades {
  /**
   * `pagina`: a estrutura inteira, enquanto a aplicação confirma quem é o usuário.
   * `cartao`: um cartão de indicador, proporcional ao KpiCard. Quem o usa anuncia o carregamento.
   * `grafico`: um ChartPanel com título, legenda e a área do gráfico. Quem o usa anuncia também.
   * `tabela`: as linhas de uma DataTable, com a mesma altura. Quem o usa anuncia o carregamento.
   */
  forma?: "pagina" | "cartao" | "grafico" | "tabela";
  /** Quantas linhas a tabela vai ter. */
  linhas?: number;
}

/** Esqueleto proporcional ao que vai aparecer, sem piscar a tela (FE §10). */
export function LoadingSkeleton({ forma = "pagina", linhas = 8 }: Propriedades) {
  if (forma === "grafico") {
    return (
      <div className={estilos.grafico} aria-hidden="true">
        <span className={`${estilos.bloco} ${estilos.tituloDoGrafico}`} />
        <span className={`${estilos.bloco} ${estilos.legendaDoGrafico}`} />
        <span className={`${estilos.bloco} ${estilos.areaDoGrafico}`} />
      </div>
    );
  }
  if (forma === "tabela") {
    return (
      <div className={estilos.tabela} aria-hidden="true">
        <span className={estilos.cabecalhoDaTabela} />
        {Array.from({ length: linhas }, (_, indice) => (
          <span key={indice} className={estilos.linhaDaTabela}>
            <span className={`${estilos.bloco} ${estilos.celulaDaTabela}`} />
          </span>
        ))}
      </div>
    );
  }
  if (forma === "cartao") {
    return (
      <div className={estilos.cartao} aria-hidden="true">
        <span className={`${estilos.bloco} ${estilos.rotuloDoCartao}`} />
        <span className={`${estilos.bloco} ${estilos.valorDoCartao}`} />
        <span className={`${estilos.bloco} ${estilos.legendaDoCartao}`} />
      </div>
    );
  }
  return (
    <div className={estilos.shell} role="status" aria-live="polite">
      <span className="visualmente-oculto">Confirmando seu acesso…</span>
      <div className={estilos.sidebar} aria-hidden="true">
        <span className={`${estilos.bloco} ${estilos.marca}`} />
        <span className={`${estilos.bloco} ${estilos.item}`} />
        <span className={`${estilos.bloco} ${estilos.rodape}`} />
      </div>
      <div className={estilos.principal} aria-hidden="true">
        <div className={estilos.topbar}>
          <span className={`${estilos.bloco} ${estilos.trilha}`} />
          <span className={`${estilos.bloco} ${estilos.chip}`} />
        </div>
        <div className={estilos.conteudo}>
          <span className={`${estilos.bloco} ${estilos.contexto}`} />
          <span className={`${estilos.bloco} ${estilos.titulo}`} />
          <span className={`${estilos.bloco} ${estilos.subtitulo}`} />
          <span className={`${estilos.bloco} ${estilos.painel}`} />
        </div>
      </div>
    </div>
  );
}
