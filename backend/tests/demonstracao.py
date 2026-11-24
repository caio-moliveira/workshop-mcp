"""Pedidos à API do ambiente para o roteiro da entrega 2 (docs/demonstracao/entrega-2.md).

Dentro de `backend/`, com o ambiente no ar:

    uv run python tests/demonstracao.py entrar ana.vendas
    uv run python tests/demonstracao.py sem-token
    uv run python tests/demonstracao.py outro-servico ana.vendas
    uv run python tests/demonstracao.py vencido

Os tokens vêm dos mesmos auxiliares dos testes: o fluxo de código com PKCE, como o navegador, e o
`admin-cli` para o token de outro serviço. Os pedidos vão à API que roda no compose, por HTTP.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
import jwt  # noqa: E402
from apoio import compose  # noqa: E402
from provedor import senha_de, token_de_outro_servico, token_pelo_fluxo_de_codigo  # noqa: E402
from recusa import pedir_eu  # noqa: E402

from acesso.validacao import FOLGA_DE_RELOGIO_EM_SEGUNDOS  # noqa: E402

API = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"
# O token guardado por `entrar`, para o pedido com token vencido. Não é versionado.
TOKEN_GUARDADO = Path(__file__).resolve().parents[1] / ".token-da-demonstracao"


def _hora(segundos: float) -> str:
    return datetime.fromtimestamp(segundos).strftime("%H:%M:%S")


def _conteudo(token: str) -> dict:
    """O conteúdo do token, sem conferir a assinatura: só para mostrar, quem confere é a API."""
    return jwt.decode(token, options={"verify_signature": False})


def _pedir_eu(token: str | None) -> None:
    """Pede GET /eu à API do ambiente e mostra a resposta e, se recusou, o motivo no log."""
    recusas_antes = len(_recusas_no_log())
    with httpx.Client(base_url=API, timeout=10) as api:
        resposta = pedir_eu(api, token)
    corpo = json.dumps(resposta.json(), ensure_ascii=False)
    print(f"GET /eu -> {resposta.status_code} {corpo}")
    if "www-authenticate" in resposta.headers:
        print(f"WWW-Authenticate: {resposta.headers['www-authenticate']}")
    if resposta.status_code == 401:
        print(f"log da API: {_nova_recusa_no_log(recusas_antes)}")


def _recusas_no_log() -> list[str]:
    """Os motivos de recusa que a API registrou: só o servidor os conhece (RS-08)."""
    log = compose("logs", "--no-log-prefix", "api").stdout
    return [
        linha.removeprefix("WARNING:api:")
        for linha in log.splitlines()
        if "token recusado" in linha
    ]


def _nova_recusa_no_log(recusas_antes: int) -> str:
    # O log do contêiner chega ao Docker com um pequeno atraso.
    for _ in range(20):
        recusas = _recusas_no_log()
        if len(recusas) > recusas_antes:
            return recusas[-1]
        time.sleep(0.5)
    return "(não encontrado)"


def entrar(nome_de_usuario: str) -> None:
    """Login pelo fluxo de código; guarda o token e pede GET /eu com ele."""
    token = token_pelo_fluxo_de_codigo(nome_de_usuario, senha_de(nome_de_usuario))
    TOKEN_GUARDADO.write_text(token, encoding="utf-8")
    conteudo = _conteudo(token)
    print(f"token de {nome_de_usuario}: aud={conteudo['aud']} vence às {_hora(conteudo['exp'])}")
    _pedir_eu(token)


def sem_token() -> None:
    _pedir_eu(None)


def outro_servico(nome_de_usuario: str) -> None:
    """Token do mesmo provedor e do mesmo usuário, emitido para o `admin-cli`."""
    token = token_de_outro_servico(nome_de_usuario, senha_de(nome_de_usuario))
    conteudo = _conteudo(token)
    destinatario = conteudo.get("aud") or "(nenhum)"
    print(f"token de {nome_de_usuario} para {conteudo['azp']}: aud={destinatario}")
    _pedir_eu(token)


def _relogio_da_api() -> float:
    """A hora no contêiner da API, em segundos desde a época."""
    resultado = compose("exec", "-T", "api", "python", "-c", "import time; print(time.time())")
    if resultado.returncode != 0:
        sys.exit(f"Não foi possível ler o relógio da API: {resultado.stderr}")
    return float(resultado.stdout)


def vencido() -> None:
    """Pede GET /eu com o token guardado por `entrar`, depois que ele venceu."""
    if not TOKEN_GUARDADO.exists():
        sys.exit("Nenhum token guardado: rode antes `entrar ana.vendas`.")
    token = TOKEN_GUARDADO.read_text(encoding="utf-8")
    conteudo = _conteudo(token)
    # Quem decide é o relógio da API, que pode andar alguns segundos atrás do da máquina, e ela
    # aceita alguns segundos de folga depois do vencimento.
    faltam = conteudo["exp"] + FOLGA_DE_RELOGIO_EM_SEGUNDOS - _relogio_da_api()
    if faltam > 0:
        sys.exit(
            f"O token ainda vale: vence às {_hora(conteudo['exp'])}. "
            f"Espere mais {int(faltam) + 1} segundos."
        )
    print(f"token de {conteudo['preferred_username']}: venceu às {_hora(conteudo['exp'])}")
    _pedir_eu(token)


COMANDOS = {
    "entrar": entrar,
    "sem-token": sem_token,
    "outro-servico": outro_servico,
    "vencido": vencido,
}

if __name__ == "__main__":
    # Acentos legíveis também quando a saída passa por um pipe no Windows.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        sys.exit(f"Uso: uv run python tests/demonstracao.py {{{'|'.join(COMANDOS)}}} [usuário]")
    COMANDOS[sys.argv[1]](*sys.argv[2:])
