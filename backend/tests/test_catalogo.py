"""O catálogo: categorias e produtos, cada produto de um lojista."""

import pytest
from apoio import contar


@pytest.mark.parametrize(("tabela", "previsto"), [("categoria", 20), ("produto", 2000)])
def test_volume_fica_dentro_de_10_por_cento_do_previsto(conexao_dono, tabela, previsto):
    assert previsto * 0.9 <= contar(conexao_dono, tabela) <= previsto * 1.1


def test_todo_produto_tem_um_lojista_uma_categoria_e_preco_positivo(conexao_dono):
    incompletos = conexao_dono.execute(
        """
        select count(*)
        from dados_de_origem.produto p
        left join dados_de_origem.lojista l on l.id = p.lojista_id
        left join dados_de_origem.categoria c on c.id = p.categoria_id
        where l.id is null or c.id is null or p.preco <= 0 or p.nome = ''
        """
    ).fetchone()[0]

    assert incompletos == 0


def test_todo_lojista_tem_ao_menos_um_produto(conexao_dono):
    sem_produto = conexao_dono.execute(
        """
        select count(*) from dados_de_origem.lojista l
        where not exists (select 1 from dados_de_origem.produto p where p.lojista_id = l.id)
        """
    ).fetchone()[0]

    assert sem_produto == 0


def test_toda_categoria_tem_produtos(conexao_dono):
    vazias = conexao_dono.execute(
        """
        select count(*) from dados_de_origem.categoria c
        where not exists (select 1 from dados_de_origem.produto p where p.categoria_id = c.id)
        """
    ).fetchone()[0]

    assert vazias == 0
