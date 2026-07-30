"""Utilitários de data: parsing tolerante e cálculo de competência (mês/ano)."""
from __future__ import annotations

from datetime import date, datetime

# Formatos aceitos na entrada (data completa ou competência mês/ano).
_FORMATOS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%Y", "%Y-%m")


def parse_data(valor) -> date | None:
    """Converte texto em ``date``; retorna ``None`` se vazio/irreconhecível.

    Aceita ISO ('2026-07-15'), BR ('15/07/2026'), datetime ('2026-07-15T10:00:00'
    ou '15/07/2026 10:00') e competência ('07/2026', '2026-07'). Em formatos de
    mês/ano, o dia é assumido como 1.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    # Descarta a parte de hora, se houver.
    texto = texto.replace("T", " ").split(" ", 1)[0]
    for fmt in _FORMATOS:
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def competencia_de(data: date | None) -> str | None:
    """Retorna a competência no formato 'MM/AAAA', ou ``None`` se sem data."""
    if data is None:
        return None
    return f"{data.month:02d}/{data.year}"


def trimestre_chave(data: date | None) -> tuple[int, int]:
    """Chave de ordenação do trimestre civil: ``(ano, trimestre)``.

    Notas sem data ficam no fim (ano/trimestre muito grandes).
    """
    if data is None:
        return (9999, 9)
    return (data.year, (data.month - 1) // 3 + 1)


def trimestre_rotulo(data: date | None) -> str:
    """Rótulo do trimestre civil da data, ex.: '2º Trim/2026 (Abr-Mai-Jun)'."""
    if data is None:
        return "Sem data"
    ano, trimestre = trimestre_chave(data)
    meses = {
        1: "Jan-Fev-Mar",
        2: "Abr-Mai-Jun",
        3: "Jul-Ago-Set",
        4: "Out-Nov-Dez",
    }[trimestre]
    return f"{trimestre}º Trim/{ano} ({meses})"
