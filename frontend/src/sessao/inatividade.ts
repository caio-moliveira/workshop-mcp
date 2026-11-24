/** Interações que contam como uso da aplicação. */
const INTERACOES = ["pointerdown", "pointermove", "keydown", "wheel", "touchstart", "scroll"];
/** De quanto em quanto tempo a inatividade é conferida, além de a cada interação. */
const INTERVALO_DE_VERIFICACAO_EM_MS = 15_000;

/**
 * Vigia a inatividade do usuário na página: só ponteiro, teclado, rolagem e a volta à aba contam
 * como uso. Passado o tempo de inatividade sem nenhuma interação, chama `aoExpirar` uma vez.
 *
 * A inatividade é conferida antes de registrar cada interação: quem volta a uma aba esquecida
 * (onde o navegador atrasa os timers) encontra a sessão já encerrada, em vez de prorrogá-la.
 */
export class VigiaDeInatividade {
  private ultimaInteracao = Date.now();
  private intervalo: number | undefined;

  constructor(
    private readonly inatividadeEmMs: number,
    private readonly aoExpirar: () => void,
    private readonly aoInteragir: () => void,
  ) {}

  iniciar(): void {
    if (this.intervalo !== undefined) return;
    this.ultimaInteracao = Date.now();
    INTERACOES.forEach((evento) =>
      window.addEventListener(evento, this.registrar, { capture: true, passive: true }),
    );
    document.addEventListener("visibilitychange", this.aoMudarDeVisibilidade);
    this.intervalo = window.setInterval(this.verificar, INTERVALO_DE_VERIFICACAO_EM_MS);
  }

  parar(): void {
    INTERACOES.forEach((evento) =>
      window.removeEventListener(evento, this.registrar, { capture: true }),
    );
    document.removeEventListener("visibilitychange", this.aoMudarDeVisibilidade);
    window.clearInterval(this.intervalo);
    this.intervalo = undefined;
  }

  /** Se houve alguma interação depois do instante dado (milissegundos desde a época). */
  interagiuDepoisDe(instante: number): boolean {
    return this.ultimaInteracao > instante;
  }

  private readonly aoMudarDeVisibilidade = (): void => {
    if (document.visibilityState === "visible") this.registrar();
  };

  private readonly registrar = (): void => {
    if (this.verificar()) return;
    this.ultimaInteracao = Date.now();
    this.aoInteragir();
  };

  /** Encerra se o tempo de inatividade passou; diz se encerrou. */
  private readonly verificar = (): boolean => {
    if (Date.now() - this.ultimaInteracao < this.inatividadeEmMs) return false;
    this.parar();
    this.aoExpirar();
    return true;
  };
}
