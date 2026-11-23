import estilos from "./Marca.module.css";

/** Monograma verde-escuro com detalhe lime e a palavra `pulso.` (FE §1 e §5). */
export function Marca() {
  return (
    <span className={estilos.marca}>
      <svg className={estilos.monograma} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
        <rect width="32" height="32" rx="8" fill="var(--brand-ink)" />
        <path
          d="M11 23V9h5.5a4.5 4.5 0 0 1 0 9H11"
          fill="none"
          stroke="var(--bg-app)"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="22.5" cy="22" r="2.2" fill="var(--accent-lime)" />
      </svg>
      <span className={estilos.nome}>pulso.</span>
    </span>
  );
}
