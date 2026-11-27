/** A busca das chamadas ao vivo do painel de segurança, de novo a cada intervalo. */
import { useEffect, useState } from "react";

import { TokenRecusado } from "../api";
import type { FonteDeDados } from "../useBloco";
import { eChamadasAoVivo, type ChamadaAoVivo } from "./contrato";

export const CAMINHO_DAS_CHAMADAS_AO_VIVO = "/seguranca/chamadas";
/** De quanto em quanto tempo a lista é buscada de novo. */
export const INTERVALO_DAS_CHAMADAS_AO_VIVO_EM_MS = 3000;

/**
 * O estado do bloco: carregando até a primeira resposta; pronto com a última lista, `atrasado`
 * quando a busca seguinte falhou; erro só se nenhuma lista chegou ainda.
 */
export type EstadoDasChamadasAoVivo =
  | { fase: "carregando" }
  | { fase: "pronto"; chamadas: ChamadaAoVivo[]; atrasado: boolean }
  | { fase: "erro" };

/** O estado depois de uma busca: a lista nova, ou a anterior marcada como atrasada. */
export function depoisDaBusca(
  anterior: EstadoDasChamadasAoVivo,
  chamadas: ChamadaAoVivo[] | null,
): EstadoDasChamadasAoVivo {
  if (chamadas) return { fase: "pronto", chamadas, atrasado: false };
  if (anterior.fase === "pronto") return { ...anterior, atrasado: true };
  return { fase: "erro" };
}

/**
 * Busca as chamadas ao vivo agora e de novo a cada intervalo, enquanto o bloco estiver na tela.
 * Com a aba escondida, não busca. Um 401 para as buscas: a sessão já está levando ao login.
 */
export function useChamadasAoVivo(
  fonte: FonteDeDados,
  intervalo: number = INTERVALO_DAS_CHAMADAS_AO_VIVO_EM_MS,
): EstadoDasChamadasAoVivo {
  const [estado, setEstado] = useState<EstadoDasChamadasAoVivo>({ fase: "carregando" });

  useEffect(() => {
    let ativo = true;
    let espera: ReturnType<typeof setTimeout> | undefined;
    async function buscar() {
      if (document.visibilityState !== "hidden") {
        try {
          const { chamadas } = await fonte.consultar(CAMINHO_DAS_CHAMADAS_AO_VIVO, eChamadasAoVivo);
          if (ativo) setEstado((anterior) => depoisDaBusca(anterior, chamadas));
        } catch (erro: unknown) {
          if (!ativo || erro instanceof TokenRecusado) return;
          setEstado((anterior) => depoisDaBusca(anterior, null));
        }
      }
      if (ativo) espera = setTimeout(buscar, intervalo);
    }
    void buscar();
    return () => {
      ativo = false;
      clearTimeout(espera);
    };
  }, [fonte, intervalo]);

  return estado;
}
