"""Orquestra o fluxo completo: ingestão -> cálculo -> relatórios."""
from __future__ import annotations

from pathlib import Path

from .calculo import aplicar_dispensa_irrf_acumulada, calcular_retencoes
from .config import PARAMETROS_PADRAO, ParametrosRetencao
from .ingestao import ler_entrada
from .models import Cabecalho, Nota, NotaCalculada
from .relatorios import exportar_excel, exportar_pdf

# Formatos de saída suportados.
FORMATOS = ("excel", "pdf", "ambos")


def calcular_notas(
    notas: list[Nota],
    parametros: ParametrosRetencao = PARAMETROS_PADRAO,
) -> list[NotaCalculada]:
    """Aplica o motor de cálculo a cada nota e a dispensa de IRRF por acúmulo."""
    calculadas = [
        NotaCalculada(nota=n, retencoes=calcular_retencoes(n, parametros))
        for n in notas
    ]
    return aplicar_dispensa_irrf_acumulada(calculadas, parametros)


def _formato_por_extensao(saida: Path) -> str:
    ext = saida.suffix.lower()
    if ext == ".pdf":
        return "pdf"
    return "excel"  # .xlsx (default)


def exportar(
    notas: list[NotaCalculada],
    saida: str | Path,
    formato: str = "auto",
    cabecalho: Cabecalho | None = None,
) -> list[Path]:
    """Exporta os relatórios no(s) formato(s) pedido(s).

    ``formato`` pode ser 'excel', 'pdf', 'ambos' ou 'auto' (deduz pela extensão).
    Retorna a lista de arquivos gerados.
    """
    saida = Path(saida)
    if formato == "auto":
        formato = _formato_por_extensao(saida)
    if formato not in FORMATOS:
        raise ValueError(f"Formato inválido: {formato!r}. Use um de {FORMATOS}.")

    gerados: list[Path] = []
    if formato in ("excel", "ambos"):
        gerados.append(exportar_excel(notas, saida.with_suffix(".xlsx"), cabecalho))
    if formato in ("pdf", "ambos"):
        gerados.append(exportar_pdf(notas, saida.with_suffix(".pdf"), cabecalho))
    return gerados


def processar(
    entrada: str | Path,
    saida: str | Path,
    parametros: ParametrosRetencao = PARAMETROS_PADRAO,
    formato: str = "auto",
    cabecalho: Cabecalho | None = None,
) -> tuple[list[Path], int]:
    """Lê a entrada, calcula as retenções e exporta o(s) relatório(s).

    Retorna ``(lista_de_arquivos_gerados, quantidade_de_notas)``.
    """
    notas = ler_entrada(entrada)
    calculadas = calcular_notas(notas, parametros)
    gerados = exportar(calculadas, saida, formato, cabecalho)
    return gerados, len(calculadas)
