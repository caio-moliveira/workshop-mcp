"""A sessão expira por inatividade: o provedor e o frontend usam o mesmo tempo (RF-09)."""

import httpx
from apoio import variavel
from provedor import administracao

TRINTA_MINUTOS = 30 * 60


def test_frontend_e_provedor_usam_os_mesmos_30_minutos_de_inatividade():
    """O frontend só renova o token de quem usou a aplicação dentro desse tempo."""
    with administracao() as admin:
        realm = admin.get("")
    realm.raise_for_status()
    configuracao = httpx.get(f"{variavel('ENDERECO_DO_FRONTEND')}/configuracao.json", timeout=10)
    configuracao.raise_for_status()

    assert realm.json()["ssoSessionIdleTimeout"] == TRINTA_MINUTOS
    assert configuracao.json()["inatividadeDaSessaoEmSegundos"] == TRINTA_MINUTOS
