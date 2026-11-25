"""A lista das conversas do usuário e a exclusão de uma conversa (RF-18, ADR 0009).

A API é criada dentro do processo, com um modelo roteirizado. O resto é de verdade: o token do
provedor do compose, o serviço `mcp` do compose e o banco `historico` do compose.
"""

import uuid

import pytest
from apoio import BANCO_DA_AUDITORIA, conectar_como_dono, valor
from chaves_locais import ChavesLocais, assinar, conteudo_valido, nova_chave
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil, UsuarioAutenticado, mensagens

CONVERSA_INEXISTENTE = {"erro": mensagens.CONVERSA_INEXISTENTE}


def listar(api, token: str):
    return api.get("/conversas", headers={"Authorization": f"Bearer {token}"})


def apagar(api, token: str, id_da_conversa: str):
    return api.delete(f"/conversas/{id_da_conversa}", headers={"Authorization": f"Bearer {token}"})


def ler(api, token: str, id_da_conversa: str):
    return api.get(f"/conversas/{id_da_conversa}", headers={"Authorization": f"Bearer {token}"})


def nova_conversa(api, token: str, pergunta: str, id_da_conversa: str | None = None) -> str:
    corpo = {"pergunta": pergunta}
    if id_da_conversa:
        corpo["id_da_conversa"] = id_da_conversa
    tipo, dados = eventos(perguntar(api, token, corpo))[0]
    assert tipo == "conversa"
    return dados["id_da_conversa"]


@pytest.fixture
def api(criar_api):
    return criar_api(modelo=modelo_roteirizado())


def test_a_lista_vem_em_ordem_de_ultima_atividade_com_titulo(api, token_de):
    token = token_de(Perfil.VENDAS)
    primeira = nova_conversa(api, token, "Quais lojistas atrasam mais?")
    segunda = nova_conversa(api, token, "Como foi o faturamento?")
    # Continuar a primeira a traz de volta ao topo.
    nova_conversa(api, token, "E no último mês?", primeira)

    resposta = listar(api, token)

    assert resposta.status_code == 200
    conversas = resposta.json()["conversas"]
    assert [(c["id"], c["titulo"]) for c in conversas[:2]] == [
        (primeira, "Quais lojistas atrasam mais?"),
        (segunda, "Como foi o faturamento?"),
    ]
    assert conversas[0]["ultima_atividade"] > conversas[1]["ultima_atividade"]


# Um usuário só dos testes, com o token assinado pelas chaves locais: a lista dele começa vazia, e
# as conversas são criadas direto no histórico, sem passar pelo modelo.
CHAVE = nova_chave()


def test_a_lista_traz_so_as_50_mais_recentes(criar_api, historico_local):
    usuario = UsuarioAutenticado(id=str(uuid.uuid4()), nome="Ana Ribeiro", perfil=Perfil.VENDAS)
    criadas = [historico_local.criar_conversa(usuario, f"Pergunta {n}") for n in range(55)]
    api = criar_api(chaves=ChavesLocais(CHAVE))
    token = assinar(conteudo_valido(sub=usuario.id), CHAVE)

    conversas = listar(api, token).json()["conversas"]

    assert [c["id"] for c in conversas] == [str(i) for i in reversed(criadas[5:])]


def test_a_lista_de_quem_nunca_perguntou_vem_vazia(criar_api):
    api = criar_api(chaves=ChavesLocais(CHAVE))

    resposta = listar(api, assinar(conteudo_valido(), CHAVE))

    assert resposta.status_code == 200
    assert resposta.json() == {"conversas": []}


def _linhas_da_auditoria() -> int:
    with conectar_como_dono(BANCO_DA_AUDITORIA) as conexao:
        return valor(conexao, "select count(*) from auditoria.chamada")


def test_apagar_tira_a_conversa_da_lista_e_da_leitura_sem_mexer_na_auditoria(criar_api, token_de):
    token = token_de(Perfil.VENDAS)
    # Com uma chamada de ferramenta: a pergunta deixa linha na auditoria.
    com_chamada = criar_api(
        modelo=modelo_roteirizado(chamadas=[("vendas_indicadores", {"periodo": "30d"})])
    )
    id_da_conversa = nova_conversa(com_chamada, token, "Como estão as vendas?")
    antes = _linhas_da_auditoria()

    resposta = apagar(com_chamada, token, id_da_conversa)

    assert resposta.status_code == 204
    assert id_da_conversa not in [c["id"] for c in listar(com_chamada, token).json()["conversas"]]
    lida = ler(com_chamada, token, id_da_conversa)
    assert lida.status_code == 404
    assert lida.json() == CONVERSA_INEXISTENTE
    assert _linhas_da_auditoria() == antes


@pytest.mark.parametrize("id_da_conversa", [str(uuid.uuid4()), "nao-e-uuid"])
def test_apagar_uma_conversa_inexistente_da_404_generico(api, token_de, id_da_conversa):
    resposta = apagar(api, token_de(Perfil.VENDAS), id_da_conversa)

    assert resposta.status_code == 404
    assert resposta.json() == CONVERSA_INEXISTENTE


def test_apagar_duas_vezes_da_404_na_segunda(api, token_de):
    token = token_de(Perfil.VENDAS)
    id_da_conversa = nova_conversa(api, token, "Vou apagar esta.")
    apagar(api, token, id_da_conversa)

    assert apagar(api, token, id_da_conversa).status_code == 404
