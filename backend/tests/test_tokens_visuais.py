"""O tema de login repete os tokens visuais do frontend (FE §2 a §4) sem divergir deles.

O Keycloak serve o tema sem enxergar o build do frontend, então o CSS do tema traz uma cópia dos
tokens. Este teste falha quando um token com o mesmo nome tem valores diferentes nos dois.
"""

import re

from apoio import RAIZ_DO_PROJETO

TOKENS_DO_FRONTEND = RAIZ_DO_PROJETO / "frontend" / "src" / "estilos" / "tokens.css"
CSS_DO_TEMA = (
    RAIZ_DO_PROJETO / "keycloak" / "temas" / "pulso" / "login" / "resources" / "css" / "pulso.css"
)


def _tokens_da_raiz(arquivo) -> dict[str, str]:
    """As propriedades customizadas do primeiro bloco `:root`, o dos valores-base."""
    texto = arquivo.read_text(encoding="utf-8")
    bloco = re.search(r"^:root\s*\{(.*?)^\}", texto, re.MULTILINE | re.DOTALL)
    assert bloco, f"{arquivo.name} sem bloco :root"
    sem_comentarios = re.sub(r"/\*.*?\*/", "", bloco.group(1), flags=re.DOTALL)
    return {
        nome: " ".join(valor.split())
        for nome, valor in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", sem_comentarios)
    }


def test_tema_de_login_usa_os_mesmos_valores_dos_tokens_do_frontend():
    frontend = _tokens_da_raiz(TOKENS_DO_FRONTEND)
    tema = _tokens_da_raiz(CSS_DO_TEMA)
    em_comum = frontend.keys() & tema.keys()

    divergentes = {
        nome: (frontend[nome], tema[nome]) for nome in em_comum if frontend[nome] != tema[nome]
    }

    assert len(em_comum) >= 20, "o tema deveria repetir os tokens do frontend"
    assert divergentes == {}, "valores (frontend, tema) diferentes"
