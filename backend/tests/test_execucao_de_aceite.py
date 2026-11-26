"""A execução de aceite contra o compose: o comando roda os cenários, mostra o andamento e o
resumo, e grava o resultado na forma prevista, sem divergência e sem token nem segredo.

O cenário do limite de frequência fica de fora: a suíte roda com o servidor MCP no limite alto,
e ele é executado no roteiro, com o limite padrão.
"""

import json
from dataclasses import replace
from datetime import date

import pytest
from apoio import variavel
from execucao_de_aceite import (
    Contexto,
    cenarios,
    cenarios_do_limite,
    conferir_carga,
    executar_cenario,
    executar_matriz_completa,
    leitura_de_rota,
    pares_da_matriz_completa,
    principal,
)
from provedor import USUARIOS_DE_DEMONSTRACAO
from registros import DONO_DA_FERRAMENTA, DONO_DA_ROTA

from aceite import ARQUIVO_DA_ULTIMA_EXECUCAO, ExecucaoDeAceite, ler_ultima_execucao
from acesso import mensagens
from servidor_mcp import limite_do_ambiente

# O nome de cada usuário de demonstração, como o token o traz e a auditoria o grava.
NOME_DO_USUARIO = {u.nome_de_usuario: u.nome for u in USUARIOS_DE_DEMONSTRACAO}
RESULTADO_NA_AUDITORIA = {"permitido": "permitida", "negado": "negada"}

SENHAS_DO_AMBIENTE = [
    "POSTGRES_PASSWORD",
    "SENHA_DO_PAPEL_VENDAS",
    "SENHA_DO_PAPEL_PRODUTOS",
    "SENHA_DO_PAPEL_COMERCIAL",
    "SENHA_DO_PAPEL_DIRETORIA",
    "SENHA_DO_PAPEL_AUDITORIA",
    "SENHA_DO_PAPEL_HISTORICO",
    "SENHA_DO_USUARIO_VENDAS",
    "SENHA_DO_USUARIO_VENDAS_VITOR",
    "SENHA_DO_USUARIO_PRODUTOS",
    "SENHA_DO_USUARIO_COMERCIAL",
    "SENHA_DO_USUARIO_DIRETORIA",
]


@pytest.fixture(scope="module")
def sem_o_limite():
    """Os cenários sem o do limite de frequência, que exige o servidor MCP no limite padrão."""
    return [c for c in cenarios() if not c.exige_limite_padrao]


@pytest.fixture(scope="module")
def execucao(sem_o_limite, tmp_path_factory):
    """O comando rodado uma vez, gravando numa pasta temporária, com a saída do terminal."""
    pasta = tmp_path_factory.mktemp("execucao-de-aceite")
    linhas: list[str] = []
    codigo = principal(["--pasta", str(pasta)], sem_o_limite, linhas.append)
    return {"codigo": codigo, "pasta": pasta, "saida": linhas}


def test_o_comando_termina_sem_divergencia(execucao):
    gravada = ler_ultima_execucao(execucao["pasta"])
    divergentes = [(c.id, c.obtido, c.resposta) for c in gravada.cenarios if c.divergencia]
    assert divergentes == []
    assert gravada.resumo.divergencias == 0
    assert execucao["codigo"] == 0


def test_cada_cenario_foi_executado_com_o_esperado(execucao, sem_o_limite):
    gravada = ler_ultima_execucao(execucao["pasta"])
    assert [(c.id, c.esperado) for c in gravada.cenarios] == [
        (c.id, c.esperado) for c in sem_o_limite
    ]
    assert gravada.resumo.executados == len(sem_o_limite)
    assert gravada.resumo.permitidos + gravada.resumo.negados == len(sem_o_limite)


def test_o_terminal_mostra_o_andamento_e_o_resumo(execucao, sem_o_limite):
    saida = execucao["saida"]
    andamento = [linha for linha in saida if linha.startswith("[")]
    assert len(andamento) == len(sem_o_limite)
    assert any("executados" in linha and "divergências" in linha for linha in saida)


def test_o_resultado_tem_a_forma_prevista(execucao):
    bruto = json.loads((execucao["pasta"] / ARQUIVO_DA_ULTIMA_EXECUCAO).read_text("utf-8"))
    assert set(bruto) == {"executada_em", "resumo", "matriz_completa", "carga", "cenarios"}
    for cenario in bruto["cenarios"]:
        assert set(cenario) == {
            "id",
            "descricao",
            "grupo",
            "quem",
            "perfil",
            "alvo",
            "camadas_de_defesa",
            "esperado",
            "obtido",
            "divergencia",
            "resposta",
            "auditoria",
            "duracao_em_ms",
        }
    # A forma lida de volta é a mesma gravada.
    assert ExecucaoDeAceite.model_validate(bruto).model_dump(mode="json") == bruto


def test_cada_chamada_traz_a_linha_da_auditoria(execucao):
    gravada = ler_ultima_execucao(execucao["pasta"])
    for cenario in gravada.cenarios:
        # A ferramenta de outro perfil pedida pelo assistente é recusada dentro da API, sem chegar
        # ao servidor MCP: não é uma chamada e não deixa linha.
        chamada = cenario.alvo.tipo == "ferramenta" or (
            cenario.alvo.tipo == "assistente" and cenario.obtido == "permitido"
        )
        if chamada:
            assert cenario.auditoria is not None, cenario.id


def test_um_cenario_permitido_traz_so_o_status_e_as_linhas(execucao):
    bruto = json.loads((execucao["pasta"] / ARQUIVO_DA_ULTIMA_EXECUCAO).read_text("utf-8"))
    permitidos = [c for c in bruto["cenarios"] if c["obtido"] == "permitido"]
    assert permitidos
    for cenario in permitidos:
        assert cenario["resposta"]["mensagem"] is None
        # O status é o HTTP, quando há: o banco e o resultado de uma ferramenta não têm.
        sem_http = cenario["alvo"]["tipo"] in {"camada_de_leitura", "dados_de_origem", "ferramenta"}
        assert cenario["resposta"]["status"] == (None if sem_http else 200), cenario["id"]
        assert isinstance(cenario["resposta"]["linhas"], int)


def test_o_resultado_nao_tem_token_nem_segredo(execucao):
    texto = (execucao["pasta"] / ARQUIVO_DA_ULTIMA_EXECUCAO).read_text("utf-8")
    # Todo token do provedor é um JWT, que começa pelo cabeçalho codificado.
    assert "eyJ" not in texto
    for nome in SENHAS_DO_AMBIENTE:
        assert variavel(nome) not in texto, nome


def test_uma_nova_execucao_substitui_a_anterior(execucao, sem_o_limite):
    anterior = ler_ultima_execucao(execucao["pasta"])
    principal(["--pasta", str(execucao["pasta"])], sem_o_limite, lambda _: None)

    nova = ler_ultima_execucao(execucao["pasta"])

    assert nova.executada_em > anterior.executada_em
    assert list(execucao["pasta"].iterdir()) == [execucao["pasta"] / ARQUIVO_DA_ULTIMA_EXECUCAO]


def test_a_matriz_completa_roda_no_comando_e_bate_com_os_registros(execucao):
    """Cada rota e cada ferramenta contra os quatro perfis: só o dono é permitido, sem
    divergência, com a data da própria execução."""
    gravada = ler_ultima_execucao(execucao["pasta"])
    itens = len(DONO_DA_ROTA) + len(DONO_DA_FERRAMENTA)

    matriz = gravada.matriz_completa

    assert matriz is not None
    assert (matriz.pares, matriz.permitidos, matriz.negados, matriz.divergencias) == (
        itens * 4,
        itens,
        itens * 3,
        0,
    )
    assert matriz.executada_em >= gravada.executada_em


def test_um_par_diferente_do_esperado_conta_como_divergencia_na_matriz():
    """Com o esperado trocado num par de rota e num de ferramenta, os dois divergem."""
    pares = pares_da_matriz_completa()
    rota = next(p for p in pares if p.tipo == "rota" and p.esperado == "negado")
    ferramenta = next(p for p in pares if p.tipo == "ferramenta" and p.esperado == "permitido")
    trocados = [replace(rota, esperado="permitido"), replace(ferramenta, esperado="negado")]
    linhas: list[str] = []

    with Contexto() as contexto:
        matriz = executar_matriz_completa(contexto, trocados, linhas.append)

    assert (matriz.pares, matriz.permitidos, matriz.negados, matriz.divergencias) == (2, 1, 1, 2)
    assert sum("DIVERGÊNCIA" in linha for linha in linhas) == 2


def test_um_resultado_diferente_do_esperado_e_gravado_como_divergencia(sem_o_limite):
    """Com o esperado trocado, o mesmo pedido diverge: a execução não esconde o resultado."""
    negado = next(c for c in sem_o_limite if c.esperado == "negado")
    trocado = replace(negado, esperado="permitido")

    with Contexto() as contexto:
        executado = executar_cenario(trocado, contexto)

    assert executado.obtido == "negado"
    assert executado.divergencia is True


def test_uma_negacao_com_outra_resposta_tambem_e_divergencia():
    """Negado, mas pela validação (400) e não pelo perfil (403): também diverge."""
    na_propria_rota = leitura_de_rota(
        "teste",
        "Período inválido na própria rota",
        "ana.vendas",
        "/vendas/indicadores",
        {"periodo": "7d"},
    )
    esperando_negacao = replace(na_propria_rota, esperado="negado")

    with Contexto() as contexto:
        executado = executar_cenario(esperando_negacao, contexto)

    assert (executado.obtido, executado.resposta.status) == ("negado", 400)
    assert executado.divergencia is True


# --- Servidor MCP: Token, Lista de ferramentas e Chamada ---


def test_a_linha_da_auditoria_traz_o_usuario_a_ferramenta_e_o_desfecho(execucao):
    """Lida pelo dono, a linha é a da chamada do cenário, permitida ou negada (CA-07)."""
    gravada = ler_ultima_execucao(execucao["pasta"])
    chamadas = [c for c in gravada.cenarios if c.grupo == "chamada"]
    assert {c.obtido for c in chamadas} == {"permitido", "negado"}
    for cenario in chamadas:
        linha = cenario.auditoria
        assert linha.usuario == NOME_DO_USUARIO[cenario.quem.nome], cenario.id
        assert linha.ferramenta == cenario.alvo.nome, cenario.id
        assert linha.argumentos == cenario.alvo.parametros, cenario.id
        assert linha.resultado == RESULTADO_NA_AUDITORIA[cenario.obtido], cenario.id


def test_a_ferramenta_de_outro_perfil_recebe_a_resposta_da_inexistente(execucao):
    por_id = {c.id: c for c in ler_ultima_execucao(execucao["pasta"]).cenarios}
    inexistente = por_id["chamada-ferramenta-inexistente"].resposta

    assert inexistente.mensagem == "Ferramenta desconhecida."
    for id in (
        "chamada-vendas-chama-ferramenta-da-diretoria",
        "chamada-diretoria-chama-ferramenta-de-vendas",
    ):
        assert por_id[id].resposta == inexistente, id


def test_os_tokens_recusados_sao_negados_com_401(execucao):
    gravada = ler_ultima_execucao(execucao["pasta"])
    de_token = [c for c in gravada.cenarios if c.grupo == "token"]
    assert len(de_token) == 3
    for cenario in de_token:
        assert (cenario.obtido, cenario.resposta.status) == ("negado", 401), cenario.id


# --- Banco, Limite de frequência, Assistente e a conferência da carga (ticket #107) ---


def test_os_cenarios_do_banco_rodam_com_a_credencial_de_cada_papel(execucao):
    gravada = ler_ultima_execucao(execucao["pasta"])
    do_banco = {c.id: c for c in gravada.cenarios if c.grupo == "banco"}
    assert len(do_banco) == 4
    assert do_banco["banco-vendas-le-a-propria-camada"].resposta.linhas == 29999
    for cenario in do_banco.values():
        assert cenario.quem.tipo == "papel"
        assert not cenario.divergencia, cenario.id
        if cenario.obtido == "negado":
            assert "42501" in cenario.resposta.mensagem, cenario.id


def test_o_assistente_chama_o_mcp_com_o_token_do_usuario(execucao):
    gravada = ler_ultima_execucao(execucao["pasta"])
    por_id = {c.id: c for c in gravada.cenarios if c.grupo == "assistente"}
    permitido = por_id["assistente-chama-o-mcp-com-o-token-do-usuario"]
    negado = por_id["assistente-ferramenta-de-outro-perfil"]

    assert (permitido.obtido, negado.obtido) == ("permitido", "negado")
    # O nome do usuário na auditoria é o do token de quem perguntou (RF-15).
    assert permitido.auditoria.usuario == "Bruno Costa"
    assert permitido.auditoria.resultado == "permitida"
    assert permitido.auditoria.ferramenta == "produtos_indicadores"
    assert negado.auditoria is None
    assert negado.camadas_de_defesa == ["lista_de_ferramentas", "chamada"]


def test_a_execucao_confere_e_registra_o_estado_da_carga(execucao):
    gravada = ler_ultima_execucao(execucao["pasta"])
    assert gravada.carga.confere is True
    assert gravada.carga.data_de_referencia == date(2026, 11, 30)
    assert gravada.carga.detalhe is None
    assert any(
        linha.startswith("Carga: o banco está no estado da carga") for linha in execucao["saida"]
    )


def test_a_conferencia_avisa_quando_o_banco_nao_esta_no_estado_da_carga():
    """Contra referências que o banco não tem, a conferência diz o que difere."""
    carga = conferir_carga(date(2025, 11, 30), {"pedido": 30000, "lead": 1500})

    assert carga.confere is False
    assert carga.data_de_referencia == date(2026, 11, 30)
    assert "2026-11-30" in carga.detalhe and "2025-11-30" in carga.detalhe
    assert "pedido com 29999 linhas, esperadas 30000" in carga.detalhe
    assert "lead" not in carga.detalhe


def test_o_cenario_do_limite_barra_o_vitor_e_a_ana_continua_passando(criar_mcp):
    """Com um servidor MCP criado no processo, no limite padrão: o do compose fica no alto."""
    servidor = criar_mcp(limite=limite_do_ambiente({}))
    vitor, ana = cenarios_do_limite(servidor)

    with Contexto() as contexto:
        barrado = executar_cenario(vitor, contexto)
        passando = executar_cenario(ana, contexto)

    assert (barrado.obtido, barrado.divergencia) == ("negado", False)
    assert barrado.resposta.mensagem == mensagens.MUITAS_CHAMADAS
    assert barrado.auditoria.resultado == "limitada"
    assert barrado.auditoria.usuario == "Vitor Nunes"
    assert (passando.obtido, passando.divergencia) == ("permitido", False)
    assert passando.auditoria.resultado == "permitida"
    assert passando.auditoria.usuario == "Ana Ribeiro"


def test_com_o_limite_alto_o_cenario_do_limite_aparece_como_divergencia(criar_mcp):
    servidor = criar_mcp(limite=limite_do_ambiente({"LIMITE_DE_CHAMADAS_POR_USUARIO": "100000"}))
    vitor, _ = cenarios_do_limite(servidor)

    with Contexto() as contexto:
        executado = executar_cenario(vitor, contexto)

    assert (executado.obtido, executado.divergencia) == ("permitido", True)
