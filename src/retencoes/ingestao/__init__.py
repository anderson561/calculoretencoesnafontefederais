"""Leitores de entrada (RF01): planilha CSV/XLSX e XML NFSe."""
from __future__ import annotations

from pathlib import Path

from ..models import Nota
from .planilha import ler_planilha
from .xml_nfse import ler_xml

_EXT_XML = {".xml"}
_EXT_PLANILHA = {".csv", ".xlsx", ".xls"}


def ler_arquivo(caminho: str | Path) -> list[Nota]:
    """Lê um arquivo de entrada escolhendo o leitor pela extensão."""
    caminho = Path(caminho)
    ext = caminho.suffix.lower()
    if ext in _EXT_XML:
        return ler_xml(caminho)
    if ext in _EXT_PLANILHA:
        return ler_planilha(caminho)
    raise ValueError(
        f"Extensão não suportada: {ext!r}. Use .xml, .csv, .xlsx ou .xls."
    )


def ler_entrada(caminho: str | Path) -> list[Nota]:
    """Lê um arquivo ou todos os arquivos suportados de um diretório."""
    caminho = Path(caminho)
    if caminho.is_dir():
        notas: list[Nota] = []
        for arquivo in sorted(caminho.iterdir()):
            if arquivo.suffix.lower() in _EXT_XML | _EXT_PLANILHA:
                notas.extend(ler_arquivo(arquivo))
        return notas
    return ler_arquivo(caminho)


__all__ = ["ler_arquivo", "ler_entrada", "ler_planilha", "ler_xml"]
