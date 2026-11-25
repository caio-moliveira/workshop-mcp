"""A avaliação maliciosa chega ao modelo marcada como texto de clientes (RS-07, CA-05, ADR 0010).

O modelo roteirizado faz o que um modelo que obedecesse ao comentário faria: depois de ler as
avaliações do produto 1 em 24 meses, tenta uma ferramenta de Vendas. Ela não está entre as
ferramentas do perfil Produtos e sai como não concluída; a API a recusa sem chegar ao servidor
MCP, e a auditoria fica só com a chamada de Produtos. O comportamento do modelo real diante do
comentário é conferido no roteiro de demonstração, não aqui.
"""

from apoio import BANCO_DA_AUDITORIA, conectar_como_dono
from provedor import conteudo
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from roteiro import eventos, modelo_roteirizado, perguntar

from acesso import Perfil

TRECHO_DA_AVALIACAO_MALICIOSA = "ignore todas as instruções anteriores"
AVALIACOES_DO_PRODUTO_1 = ("produtos_avaliacoes", {"produto": 1, "periodo": "24m"})
FERRAMENTA_DE_VENDAS = ("vendas_indicadores", {"periodo": "30d"})


def _ultimo_id() -> int:
    with conectar_como_dono(BANCO_DA_AUDITORIA) as conexao:
        return conexao.execute("select coalesce(max(id), 0) from auditoria.chamada").fetchone()[0]


def _chamadas_desde(id_do_usuario: str, depois_do_id: int) -> list[dict]:
    with conectar_como_dono(BANCO_DA_AUDITORIA) as conexao:
        cursor = conexao.execute(
            "select * from auditoria.chamada where id_do_usuario = %s and id > %s order by id",
            (id_do_usuario, depois_do_id),
        )
        nomes = [coluna.name for coluna in cursor.description]
        return [dict(zip(nomes, linha, strict=True)) for linha in cursor.fetchall()]


def _retornos(vistos: dict) -> dict[str, ToolReturnPart]:
    """O que voltou ao modelo de cada ferramenta que ele chamou, pelo nome da ferramenta."""
    return {
        parte.tool_name: parte
        for mensagem in vistos["mensagens"]
        if isinstance(mensagem, ModelRequest)
        for parte in mensagem.parts
        if hasattr(parte, "tool_name")
    }


def test_o_comentario_malicioso_chega_ao_modelo_com_o_aviso_e_nao_abre_outro_perfil(
    criar_api, token_de
):
    token = token_de(Perfil.PRODUTOS)
    do_token = conteudo(token)
    antes = _ultimo_id()
    vistos: dict = {}
    api = criar_api(
        modelo=modelo_roteirizado(
            chamadas=[AVALIACOES_DO_PRODUTO_1, FERRAMENTA_DE_VENDAS],
            pedacos=["Ok."],
            vistos=vistos,
        )
    )

    lidos = eventos(perguntar(api, token, {"pergunta": "O que dizem do produto 1?"}))

    assert lidos[-1][0] == "fim"
    retornos = _retornos(vistos)
    das_avaliacoes = retornos[AVALIACOES_DO_PRODUTO_1[0]]
    assert das_avaliacoes.outcome == "success"
    resultado = das_avaliacoes.content
    assert "clientes" in resultado["aviso"]
    comentarios = [a["comentario"] or "" for a in resultado["avaliacoes"]]
    assert any(TRECHO_DA_AVALIACAO_MALICIOSA in c.lower() for c in comentarios)
    assert retornos[FERRAMENTA_DE_VENDAS[0]].outcome != "success"

    [linha] = _chamadas_desde(do_token["sub"], antes)
    assert linha["ferramenta"] == AVALIACOES_DO_PRODUTO_1[0]
    assert linha["parametros"] == AVALIACOES_DO_PRODUTO_1[1]
    assert linha["resultado"] == "permitida"
    assert linha["nome_do_usuario"] == do_token["name"]
    assert linha["perfil"] == "produtos"
