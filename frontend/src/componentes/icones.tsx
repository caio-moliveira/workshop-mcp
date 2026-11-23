/** Ícones lineares de mesmo peso (FE §5), desenhados à mão: sem biblioteca de ícones. */
import type { SVGProps } from "react";

function Icone(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    />
  );
}

export function IconePainel() {
  return (
    <Icone>
      <path d="M4 20V10M10 20V4M16 20v-7M21 20H3" />
    </Icone>
  );
}

export function IconeMenu() {
  return (
    <Icone>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Icone>
  );
}

export function IconeFechar() {
  return (
    <Icone>
      <path d="M6 6l12 12M18 6L6 18" />
    </Icone>
  );
}

export function IconeSair() {
  return (
    <Icone>
      <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l-4-4 4-4M6 12h10" />
    </Icone>
  );
}

export function IconeAviso() {
  return (
    <Icone>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v5.5M12 16.5v.01" />
    </Icone>
  );
}

export function IconeEmBreve() {
  return (
    <Icone>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </Icone>
  );
}
