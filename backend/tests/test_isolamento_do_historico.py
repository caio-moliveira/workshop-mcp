"""Isolamento do histórico: um usuário não alcança a conversa de outro (RF-18, ADR 0009).

Em listar, ler, continuar e apagar: entre dois usuários do mesmo perfil, entre usuários de perfis
diferentes e entre perfis do mesmo `sub`. A recusa é sempre a de uma conversa que não existe, para
não revelar que ela existe. Mais as recusas de token e do CORS nas rotas do histórico.
"""

import uuid

import jwt
import pytest
from apoio import variavel
from chaves_locais import ChavesLocais, assinar, conteudo_valido, nova_chave
from provedor import OUTRA_APLICACAO, senha_de, token_pelo_fluxo_de_codigo
from recusa import assert_recusado
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil, UsuarioAutenticado, mensagens

CONVERSA_INEXISTENTE = {"erro": mensagens.CONVERSA_INEXISTENTE}


def _cabecalhos(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def listar(api, token):
    return api.get("/conversas", headers=_cabecalhos(token))


def ler(api, token, id_da_conversa: str):
    return api.get(f"/conversas/{id_da_conversa}", headers=_cabecalhos(token))


def apagar(api, token, id_da_conversa: str):
    return api.delete(f"/conversas/{id_da_conversa}", headers=_cabecalhos(token))


def continuar(api, token, id_da_conversa: str):
    return perguntar(api, token, {"pergunta": "E agora?", "id_da_conversa": id_da_conversa})


@pytest.fixture(scope="module")
def token_do_usuario():
    """O token de um usuário de demonstração pelo nome, guardado no módulo."""
    guardados: dict[str, str] = {}

    def token(nome_de_usuario: str) -> str:
        if nome_de_usuario not in guardados:
            guardados[nome_de_usuario] = token_pelo_fluxo_de_codigo(
                nome_de_usuario, senha_de(nome_de_usuario)
            )
        return guardados[nome_de_usuario]

    return token


@pytest.fixture
def api(criar_api):
    return criar_api(modelo=modelo_roteirizado())


def _assert_como_inexistente(resposta) -> None:
    assert resposta.status_code == 404
    assert resposta.json() == CONVERSA_INEXISTENTE


def _assert_nao_alcanca(api, token_do_outro: str, id_da_conversa: str) -> None:
    """O outro não vê a conversa na lista e recebe, em ler, continuar e apagar, a mesma recusa de
    uma conversa que não existe."""
    assert id_da_conversa not in [c["id"] for c in listar(api, token_do_outro).json()["conversas"]]
    inexistente = str(uuid.uuid4())
    for pedir in (ler, continuar, apagar):
        alheia = pedir(api, token_do_outro, id_da_conversa)
        _assert_como_inexistente(alheia)
        assert alheia.json() == pedir(api, token_do_outro, inexistente).json()


@pytest.mark.parametrize(
    ("dono", "outro"),
    [
        ("ana.vendas", "vitor.vendas"),
        ("vitor.vendas", "ana.vendas"),
        ("ana.vendas", "bruno.produtos"),
        ("bruno.produtos", "ana.vendas"),
    ],
)
def test_um_usuario_nao_alcanca_a_conversa_de_outro(api, token_do_usuario, dono, outro):
    token_do_dono = token_do_usuario(dono)
    tipo, dados = eventos(perguntar(api, token_do_dono, {"pergunta": f"Conversa de {dono}"}))[0]
    assert tipo == "conversa"
    id_da_conversa = dados["id_da_conversa"]

    _assert_nao_alcanca(api, token_do_usuario(outro), id_da_conversa)

    # Nada do que o outro tentou mudou a conversa do dono.
    lida = ler(api, token_do_dono, id_da_conversa)
    assert lida.status_code == 200
    assert [item["texto"] for item in lida.json()["itens"]][0] == f"Conversa de {dono}"
    assert len(lida.json()["itens"]) == 2


# O mesmo `sub` com outro perfil só existe com um token assinado pelas chaves locais: o provedor
# real dá a cada usuário um perfil só. A conversa é criada direto no histórico, sem o modelo.
CHAVE = nova_chave()


def test_o_mesmo_usuario_com_outro_perfil_nao_alcanca_as_conversas_do_perfil_antigo(
    criar_api, historico_local
):
    sub = str(uuid.uuid4())
    como_vendas = UsuarioAutenticado(id=sub, nome="Ana Ribeiro", perfil=Perfil.VENDAS)
    id_da_conversa = str(historico_local.criar_conversa(como_vendas, "Do tempo de Vendas"))
    api = criar_api(chaves=ChavesLocais(CHAVE), modelo=modelo_roteirizado())
    token_de_vendas = assinar(conteudo_valido(sub=sub, perfil="vendas"), CHAVE)
    token_de_produtos = assinar(conteudo_valido(sub=sub, perfil="produtos"), CHAVE)

    _assert_nao_alcanca(api, token_de_produtos, id_da_conversa)

    assert ler(api, token_de_vendas, id_da_conversa).status_code == 200


# Recusas de token: as mesmas das demais rotas (RS-01, CA-03).

ROTAS_DO_HISTORICO = [
    ("GET", "/conversas"),
    ("GET", "/conversas/{id}"),
    ("DELETE", "/conversas/{id}"),
]


def _pedir(api, metodo: str, caminho: str, token: str | None):
    return api.request(metodo, caminho.format(id=uuid.uuid4()), headers=_cabecalhos(token))


@pytest.mark.parametrize(("metodo", "caminho"), ROTAS_DO_HISTORICO)
def test_sem_token_as_rotas_do_historico_recusam(api, metodo, caminho):
    assert_recusado(_pedir(api, metodo, caminho, None))


@pytest.mark.parametrize(("metodo", "caminho"), ROTAS_DO_HISTORICO)
def test_com_token_vencido_as_rotas_do_historico_recusam(
    criar_api, token_do_usuario, metodo, caminho
):
    token = token_do_usuario("ana.vendas")
    vencimento = jwt.decode(token, options={"verify_signature": False})["exp"]
    api = criar_api(relogio=lambda: vencimento + 60)

    assert_recusado(_pedir(api, metodo, caminho, token))


@pytest.mark.parametrize(("metodo", "caminho"), ROTAS_DO_HISTORICO)
def test_com_token_de_outra_aplicacao_as_rotas_do_historico_recusam(api, metodo, caminho):
    token = token_pelo_fluxo_de_codigo("ana.vendas", senha_de("ana.vendas"), OUTRA_APLICACAO)

    assert_recusado(_pedir(api, metodo, caminho, token))


# A requisição prévia do navegador para apagar: só a origem do frontend passa.


def _consulta_previa_do_delete(api, origem: str):
    return api.options(
        f"/conversas/{uuid.uuid4()}",
        headers={
            "Origin": origem,
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "authorization",
        },
    )


def test_a_consulta_previa_do_delete_passa_da_origem_do_frontend(api):
    origem = variavel("ENDERECO_DO_FRONTEND")

    resposta = _consulta_previa_do_delete(api, origem)

    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == origem
    assert "DELETE" in resposta.headers["access-control-allow-methods"]


def test_a_consulta_previa_do_delete_nao_passa_de_outra_origem(api):
    resposta = _consulta_previa_do_delete(api, "http://site-estranho.example")

    assert "access-control-allow-origin" not in resposta.headers
