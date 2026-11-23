import estilos from "./LoadingSkeleton.module.css";

/** Esqueleto da estrutura enquanto a aplicação confirma quem é o usuário (FE §10). */
export function LoadingSkeleton() {
  return (
    <div className={estilos.shell} role="status" aria-live="polite">
      <span className={estilos.oculto}>Confirmando seu acesso…</span>
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
