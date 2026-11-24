"""Negar é o padrão: toda ferramenta publicada vem do registro e serve uma consulta com perfil.

Uma ferramenta nova sem consulta, com parâmetro livre ou sem descrição faz estes testes falharem
antes de ser publicada (RF-23, RF-24, RS-05). O que o servidor publica é lido pelo protocolo, como
um cliente MCP o vê.
"""

import pytest
from chaves_locais import ChavesLocais, assinar, conteudo_valido, nova_chave
from cliente_mcp import (
    FERRAMENTA_DESCONHECIDA,
    chamar,
    listar_ferramentas,
    pedir_ao_protocolo,
    texto_do_erro,
)
from provedor import DESTINATARIO_DO_MCP, emissor
from starlette.testclient import TestClient

from acesso import ConfiguracaoDeAcesso, Perfil
from consultas import Consulta
from servidor_mcp.ferramentas import FERRAMENTAS, PERIODO, Ferramenta
from servidor_mcp.servidor import criar_servidor

CHAVE = nova_chave()

# Os parâmetros previstos de cada ferramenta, repetidos aqui de propósito: publicar uma ferramenta
# ou um parâmetro novo exige mudar também este teste.
PARAMETROS_PREVISTOS = {
    "vendas_indicadores": {"periodo"},
    "vendas_atrasos": {"periodo", "agrupamento"},
}
# Os valores de cada parâmetro, também repetidos: a enumeração é fechada.
VALORES_PREVISTOS = {
    "periodo": ["30d", "90d", "12m", "24m"],
    "agrupamento": ["rota", "lojista"],
}
PADROES_PREVISTOS = {"periodo": "12m"}
# Os parâmetros sem padrão, que quem chama precisa informar.
OBRIGATORIOS_PREVISTOS = {"vendas_atrasos": {"agrupamento"}}


def token_de(perfil: Perfil) -> str:
    return assinar(conteudo_valido(aud=DESTINATARIO_DO_MCP, perfil=perfil.value), CHAVE)


@pytest.fixture(scope="module")
def publicadas(criar_mcp) -> dict[Perfil, list]:
    """As ferramentas que o servidor lista para cada perfil."""
    mcp = criar_mcp(chaves=ChavesLocais(CHAVE))
    return {perfil: listar_ferramentas(mcp, token_de(perfil)) for perfil in Perfil}


@pytest.fixture(scope="module")
def ferramentas(publicadas) -> list:
    return [ferramenta for do_perfil in publicadas.values() for ferramenta in do_perfil]


def test_o_registro_e_o_esperado():
    assert set(FERRAMENTAS) == set(PARAMETROS_PREVISTOS)


def test_toda_ferramenta_publicada_vem_do_registro_e_tem_consulta_com_perfil(publicadas):
    assert any(publicadas.values())
    for perfil, do_perfil in publicadas.items():
        for publicada in do_perfil:
            registrada = FERRAMENTAS[publicada.name]
            assert isinstance(registrada.consulta, Consulta), publicada.name
            assert isinstance(registrada.consulta.perfil, Perfil), publicada.name
            assert registrada.consulta.perfil is perfil, publicada.name


def test_toda_ferramenta_do_registro_e_publicada_so_para_o_perfil_da_consulta(publicadas):
    for nome, registrada in FERRAMENTAS.items():
        quem_ve = {p for p, do_perfil in publicadas.items() if nome in {f.name for f in do_perfil}}
        assert quem_ve == {registrada.consulta.perfil}, nome


def test_o_nome_de_toda_ferramenta_comeca_pelo_perfil():
    """ADR 0005: o prefixo evita colisão com as ferramentas dos próximos perfis."""
    for nome, registrada in FERRAMENTAS.items():
        assert nome.startswith(f"{registrada.consulta.perfil.value}_"), nome


def test_o_esquema_de_entrada_so_tem_os_parametros_previstos(ferramentas):
    for ferramenta in ferramentas:
        esquema = ferramenta.input_schema
        assert esquema["type"] == "object", ferramenta.name
        assert esquema["additionalProperties"] is False, ferramenta.name
        assert set(esquema["properties"]) == PARAMETROS_PREVISTOS[ferramenta.name], ferramenta.name
        obrigatorios = OBRIGATORIOS_PREVISTOS.get(ferramenta.name, set())
        assert set(esquema.get("required", [])) == obrigatorios, ferramenta.name
        assert set(esquema) <= {"type", "properties", "additionalProperties", "required"}


def test_todo_parametro_e_uma_enumeracao_fechada(ferramentas):
    for ferramenta in ferramentas:
        for nome, parametro in ferramenta.input_schema["properties"].items():
            onde = f"{ferramenta.name}.{nome}"
            assert parametro["type"] == "string", onde
            assert parametro["enum"] == VALORES_PREVISTOS[nome], onde
            assert set(parametro) <= {"type", "enum", "description", "default"}, onde


def test_o_periodo_e_opcional_com_padrao_de_12_meses(ferramentas):
    for ferramenta in ferramentas:
        esquema = ferramenta.input_schema
        assert "periodo" in esquema["properties"], ferramenta.name
        assert "periodo" not in esquema.get("required", []), ferramenta.name
        assert esquema["properties"]["periodo"]["default"] == PADROES_PREVISTOS["periodo"]


def test_parametro_sem_padrao_e_obrigatorio():
    obrigatorio = Ferramenta(
        consulta=FERRAMENTAS["vendas_indicadores"].consulta,
        titulo="Exemplo",
        descricao="Exemplo.",
        parametros=(PERIODO, type(PERIODO)("corte", PERIODO.enumeracao, "Exemplo.")),
    )

    assert obrigatorio.esquema_de_entrada()["required"] == ["corte"]


def test_ferramenta_e_parametros_tem_descricao_para_o_modelo(ferramentas):
    for ferramenta in ferramentas:
        assert len(ferramenta.description or "") >= 80, ferramenta.name
        assert ferramenta.title, ferramenta.name
        for nome, parametro in ferramenta.input_schema["properties"].items():
            assert len(parametro.get("description", "")) >= 40, f"{ferramenta.name}.{nome}"


def test_toda_ferramenta_se_declara_somente_leitura(ferramentas):
    for ferramenta in ferramentas:
        assert ferramenta.annotations.read_only_hint is True, ferramenta.name


def test_uma_ferramenta_sem_consulta_nao_pode_ser_registrada():
    def leitura_solta(conexao, periodo): ...

    for sem_consulta in (leitura_solta, None, "indicadores"):
        with pytest.raises(TypeError):
            Ferramenta(
                consulta=sem_consulta, titulo="Solta", descricao="Solta.", parametros=(PERIODO,)
            )


def test_uma_ferramenta_fora_do_registro_nao_e_publicada(executor_de_consultas):
    """Mesmo acrescentada direto ao servidor, por engano, ela não é listada nem chamada."""
    configuracao = ConfiguracaoDeAcesso(
        emissor=emissor(), destinatario=DESTINATARIO_DO_MCP, chaves=ChavesLocais(CHAVE)
    )
    servidor = criar_servidor(configuracao, executor_de_consultas)

    @servidor.tool
    def consulta_livre(sql: str) -> str:
        return "executada"

    mcp = servidor.http_app(path="/mcp", stateless_http=True, json_response=True)
    token = token_de(Perfil.VENDAS)

    assert [f.name for f in listar_ferramentas(mcp, token)] == list(FERRAMENTAS)
    resultado = chamar(mcp, token, "consulta_livre", {"sql": "select 1"})
    assert texto_do_erro(resultado) == FERRAMENTA_DESCONHECIDA


def test_o_servidor_so_expoe_ferramentas(criar_mcp):
    with TestClient(criar_mcp(chaves=ChavesLocais(CHAVE))) as http:
        token = token_de(Perfil.VENDAS)
        recursos = pedir_ao_protocolo(http, token, "resources/list").json()["result"]
        modelos = pedir_ao_protocolo(http, token, "resources/templates/list").json()["result"]
        prompts = pedir_ao_protocolo(http, token, "prompts/list").json()["result"]

    assert recursos["resources"] == []
    assert modelos["resourceTemplates"] == []
    assert prompts["prompts"] == []
