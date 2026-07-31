"""Verificação opcional de nova versão via GitHub Releases.

Não bloqueante e de falha silenciosa: o aplicativo roda 100% offline, então
qualquer problema de rede (sem internet, GitHub fora do ar, timeout) apenas
resulta em nenhum aviso — nunca uma exceção que atrapalhe o uso normal.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from urllib.error import URLError

from . import __version__

_URL_RELEASE_MAIS_RECENTE = (
    "https://api.github.com/repos/anderson561/calculoretencoesnafontefederais"
    "/releases/latest"
)
_TIMEOUT_SEGUNDOS = 3


@dataclass(frozen=True)
class InfoAtualizacao:
    versao_atual: str
    versao_disponivel: str
    url_download: str


def _versao_para_tupla(versao: str) -> tuple[int, ...]:
    partes = versao.strip().lstrip("vV").split(".")
    return tuple(int(p) for p in partes if p.isdigit())


def verificar_atualizacao() -> InfoAtualizacao | None:
    """Consulta a última release publicada no GitHub.

    Devolve ``None`` se a versão instalada já é a mais recente, ou se a
    checagem falhar por qualquer motivo (offline, GitHub indisponível,
    resposta inesperada etc.).
    """
    try:
        requisicao = urllib.request.Request(
            _URL_RELEASE_MAIS_RECENTE,
            headers={"Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(requisicao, timeout=_TIMEOUT_SEGUNDOS) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError, OSError):
        return None

    tag = dados.get("tag_name")
    url = dados.get("html_url")
    if not tag or not url:
        return None

    versao_disponivel = _versao_para_tupla(tag)
    if not versao_disponivel or versao_disponivel <= _versao_para_tupla(__version__):
        return None

    return InfoAtualizacao(
        versao_atual=__version__,
        versao_disponivel=tag.lstrip("vV"),
        url_download=url,
    )
