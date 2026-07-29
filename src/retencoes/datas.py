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
