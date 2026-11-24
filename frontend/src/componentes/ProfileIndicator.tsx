import { corDoPerfil, DESCRICAO_DOS_PERFIS, type Perfil } from "../perfis";
import estilos from "./ProfileIndicator.module.css";

interface Propriedades {
  perfil: Perfil;
  /** Com o nome, mostra avatar, nome e perfil (rodapé da sidebar); sem ele, só o chip do perfil. */
  nome?: string;
}

function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/);
  const primeira = partes[0]?.[0] ?? "";
  const ultima = partes.length > 1 ? (partes[partes.length - 1]?.[0] ?? "") : "";
  return (primeira + ultima).toUpperCase();
}

/** Mostra o perfil atual com a cor de identificação do perfil (FE §2), só em detalhes. */
export function ProfileIndicator({ perfil, nome }: Propriedades) {
  const descricao = DESCRICAO_DOS_PERFIS[perfil];

  if (nome === undefined) {
    return (
      <span className={estilos.chip} style={corDoPerfil(perfil)}>
        <span className={estilos.ponto} aria-hidden="true" />
        <span>
          <span className="visualmente-oculto">Perfil </span>
          {descricao.nome}
        </span>
      </span>
    );
  }

  return (
    <div className={estilos.completo} style={corDoPerfil(perfil)}>
      <span className={estilos.avatar} aria-hidden="true">
        {iniciais(nome)}
      </span>
      <span className={estilos.identificacao}>
        <span className={estilos.nome}>{nome}</span>
        <span className={estilos.perfil}>
          <span className={estilos.linha} aria-hidden="true" />
          <span className="visualmente-oculto">Perfil </span>
          {descricao.nome}
        </span>
      </span>
    </div>
  );
}
