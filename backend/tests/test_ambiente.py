"""O ambiente sobe com um comando e a carga deixa o banco pronto."""

from apoio import compose, conectar_como_dono


def test_banco_carregado_tem_o_esquema_dos_dados_de_origem(conexao_dono):
    esquemas = {
        linha[0]
        for linha in conexao_dono.execute("select schema_name from information_schema.schemata")
    }

    assert "dados_de_origem" in esquemas


def test_carga_que_falha_termina_com_erro_visivel():
    resultado = compose("run", "--rm", "-e", "POSTGRES_PASSWORD=senha-errada", "carga")

    assert resultado.returncode != 0
    assert "carga: falhou" in resultado.stderr


def test_rodar_a_carga_de_novo_derruba_e_recria_tudo():
    with conectar_como_dono() as conexao:
        conexao.execute("create table dados_de_origem.resto_de_outra_execucao (id int)")

    resultado = compose("run", "--rm", "carga")

    assert resultado.returncode == 0, resultado.stderr
    with conectar_como_dono() as conexao:
        tabelas = conexao.execute(
            "select table_name from information_schema.tables"
            " where table_schema = 'dados_de_origem'"
        ).fetchall()
    assert tabelas == []


def test_banco_so_e_publicado_no_endereco_local():
    resultado = compose("port", "postgres", "5432")

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip().startswith("127.0.0.1:")
