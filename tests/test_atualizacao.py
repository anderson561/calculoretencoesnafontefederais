import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from retencoes import __version__
from retencoes.atualizacao import verificar_atualizacao


def _resposta_github(tag_name: str, html_url: str = "https://github.com/x/y/releases/tag/v9.9.9"):
    corpo = json.dumps({"tag_name": tag_name, "html_url": html_url}).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = corpo
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def test_versao_mais_nova_disponivel():
    tag_mais_nova = "v999.0.0"
    with patch("retencoes.atualizacao.urllib.request.urlopen", return_value=_resposta_github(tag_mais_nova)):
        info = verificar_atualizacao()

    assert info is not None
    assert info.versao_atual == __version__
    assert info.versao_disponivel == "999.0.0"
    assert info.url_download.startswith("https://")


def test_versao_atual_ja_e_a_mais_recente():
    with patch("retencoes.atualizacao.urllib.request.urlopen", return_value=_resposta_github(f"v{__version__}")):
        info = verificar_atualizacao()

    assert info is None


def test_versao_disponivel_mais_antiga_nao_gera_aviso():
    with patch("retencoes.atualizacao.urllib.request.urlopen", return_value=_resposta_github("v0.0.1")):
        info = verificar_atualizacao()

    assert info is None


def test_falha_de_rede_nao_lanca_excecao():
    with patch("retencoes.atualizacao.urllib.request.urlopen", side_effect=URLError("sem internet")):
        info = verificar_atualizacao()

    assert info is None


def test_resposta_sem_tag_nao_lanca_excecao():
    with patch("retencoes.atualizacao.urllib.request.urlopen", return_value=_resposta_github("")):
        info = verificar_atualizacao()

    assert info is None
