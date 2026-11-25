"""Pedidos à API do ambiente para os roteiros das entregas 2, 3 e 8 (docs/demonstracao/).

Dentro de `backend/`, com o ambiente no ar:

    uv run python tests/demonstracao.py entrar ana.vendas
    uv run python tests/demonstracao.py sem-token
    uv run python tests/demonstracao.py outro-servico ana.vendas
    uv run python tests/demonstracao.py vencido
    uv run python tests/demonstracao.py vendas ana.vendas [periodo]
    uv run python tests/demonstracao.py tempos [periodo] [perfil]

Os tokens vêm dos mesmos auxiliares dos testes: o fluxo de código com PKCE, como o navegador, e o
`admin-cli` para o token de outro serviço. Os pedidos vão à API que roda no compose, por HTTP.
"""

import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from apoio import compose  # noqa: E402
from provedor import (  # noqa: E402
    conteudo,
    destinatarios,
    senha_de,
    token_de_outro_servico,
    token_pelo_fluxo_de_codigo,
    usuario_de,
)
from recusa import ROTAS_DE_VENDAS, pedir, pedir_eu  # noqa: E402
from registros import DONO_DA_ROTA  # noqa: E402

from acesso import Perfil  # noqa: E402
from acesso.validacao import FOLGA_DE_RELOGIO_EM_SEGUNDOS  # noqa: E402

API = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"
# O token guardado por `entrar`, para o pedido com token vencido. Não é versionado.
TOKEN_GUARDADO = Path(__file__).resolve().parents[1] / ".token-da-demonstracao"


def _hora(segundos: float) -> str:
    return datetime.fromtimestamp(segundos).strftime("%H:%M:%S")


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
    do_token = conteudo(token)
    aud = ", ".join(destinatarios(do_token))
    print(f"token de {nome_de_usuario}: aud={aud} vence às {_hora(do_token['exp'])}")
    _pedir_eu(token)


def sem_token() -> None:
    _pedir_eu(None)


def outro_servico(nome_de_usuario: str) -> None:
    """Token do mesmo provedor e do mesmo usuário, emitido para o `admin-cli`."""
    token = token_de_outro_servico(nome_de_usuario, senha_de(nome_de_usuario))
    do_token = conteudo(token)
    aud = ", ".join(destinatarios(do_token)) or "(nenhum)"
    print(f"token de {nome_de_usuario} para {do_token['azp']}: aud={aud}")
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
    do_token = conteudo(token)
    # Quem decide é o relógio da API, que pode andar alguns segundos atrás do da máquina, e ela
    # aceita alguns segundos de folga depois do vencimento.
    faltam = do_token["exp"] + FOLGA_DE_RELOGIO_EM_SEGUNDOS - _relogio_da_api()
    if faltam > 0:
        sys.exit(
            f"O token ainda vale: vence às {_hora(do_token['exp'])}. "
            f"Espere mais {int(faltam) + 1} segundos."
        )
    print(f"token de {do_token['preferred_username']}: venceu às {_hora(do_token['exp'])}")
    _pedir_eu(token)


def _resumo_de_vendas(rota: str, corpo: dict) -> str:
    """Uma linha com o essencial de cada bloco do painel, para não despejar o JSON inteiro."""
    if rota == "/vendas/indicadores":
        pedidos = corpo["pedidos_realizados"]["atual"]
        receita = corpo["receita"]["atual"]
        aprovacao = corpo["taxa_de_aprovacao"]["atual"]
        return f"{pedidos} pedidos, receita {receita:.2f}, aprovação {aprovacao:.3f}"
    if rota == "/vendas/evolucao":
        return f"{len(corpo['pontos'])} pontos por {corpo['agrupamento']}"
    if rota == "/vendas/situacao-das-entregas":
        return ", ".join(f"{s['situacao']} {s['pedidos']}" for s in corpo["situacoes"])
    return f"{len(corpo['pedidos'])} pedidos, o mais recente {corpo['pedidos'][0]['numero']}"


def vendas(nome_de_usuario: str, periodo: str = "12m") -> None:
    """Login pelo fluxo de código e as quatro rotas de Vendas com o token desse usuário."""
    token = token_pelo_fluxo_de_codigo(nome_de_usuario, senha_de(nome_de_usuario))
    print(f"token de {nome_de_usuario}: perfil={conteudo(token)['perfil']}")
    with httpx.Client(base_url=API, timeout=10) as api:
        for rota in ROTAS_DE_VENDAS:
            resposta = pedir(api, rota, token, periodo=periodo)
            if resposta.status_code == 200:
                corpo = _resumo_de_vendas(rota, resposta.json())
            else:
                corpo = json.dumps(resposta.json(), ensure_ascii=False)
            print(f"GET {rota}?periodo={periodo} -> {resposta.status_code} {corpo}")


MEDICOES_POR_ROTA = 5


def tempos(periodo: str = "24m", perfil: str = "vendas") -> None:
    """O tempo de cada rota do perfil na API do ambiente, como usuário desse perfil (RNF-05).

    As rotas vêm do registro da API: as do perfil pedido (Vendas, por padrão). Um pedido de
    aquecimento por rota (pool de conexões e chaves do provedor), depois `MEDICOES_POR_ROTA`
    pedidos medidos do lado de quem chama, com a rede local incluída.
    """
    dono = Perfil(perfil)
    rotas = [rota for rota, perfil_da_rota in DONO_DA_ROTA.items() if perfil_da_rota is dono]
    usuario = usuario_de(dono)
    token = token_pelo_fluxo_de_codigo(usuario.nome_de_usuario, usuario.senha())
    print(f"{MEDICOES_POR_ROTA} pedidos por rota, periodo={periodo}, meta 3 s (RNF-05)")
    with httpx.Client(base_url=API, timeout=30) as api:
        for rota in rotas:
            pedir(api, rota, token, periodo=periodo).raise_for_status()
            duracoes = []
            for _ in range(MEDICOES_POR_ROTA):
                inicio = time.perf_counter()
                pedir(api, rota, token, periodo=periodo).raise_for_status()
                duracoes.append(time.perf_counter() - inicio)
            mediana, maximo = statistics.median(duracoes) * 1000, max(duracoes) * 1000
            print(f"{rota:<32} mediana {mediana:5.0f} ms  máximo {maximo:5.0f} ms")


COMANDOS = {
    "entrar": entrar,
    "sem-token": sem_token,
    "outro-servico": outro_servico,
    "vencido": vencido,
    "vendas": vendas,
    "tempos": tempos,
}

if __name__ == "__main__":
    # Acentos legíveis também quando a saída passa por um pipe no Windows.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        sys.exit(f"Uso: uv run python tests/demonstracao.py {{{'|'.join(COMANDOS)}}} [usuário]")
    COMANDOS[sys.argv[1]](*sys.argv[2:])
