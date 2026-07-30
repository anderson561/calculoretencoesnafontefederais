"""Orquestra o fluxo completo: ingestão -> cálculo -> relatório (PDF)."""
from __future__ import annotations

from pathlib import Path

from .calculo import aplicar_dispensa_irrf_acumulada, calcular_retencoes
from .config import PARAMETROS_PADRAO, ParametrosRetencao
from .ingestao import ler_entrada
from .models import Cabecalho, Nota, NotaCalculada
from .relatorios import exportar_pdf


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


def exportar(
    notas: list[NotaCalculada],
    saida: str | Path,
    cabecalho: Cabecalho | None = None,
) -> list[Path]:
    """Exporta o relatório em PDF. Retorna a lista com o arquivo gerado."""
    saida = Path(saida).with_suffix(".pdf")
    return [exportar_pdf(notas, saida, cabecalho)]


def montar_cabecalho(notas: list[Nota]) -> Cabecalho:
    """Monta o cabeçalho a partir do prestador extraído das notas (XML).

    Usa o primeiro prestador encontrado; em planilhas (sem prestador) devolve
    um cabeçalho em branco (só a data de emissão será exibida).
    """
    for n in notas:
        if n.prestador_nome or n.prestador_cnpj:
            return Cabecalho(prestador=n.prestador_nome or "", cnpj=n.prestador_cnpj or "")
    return Cabecalho()


def processar(
    entrada: str | Path,
    saida: str | Path,
    parametros: ParametrosRetencao = PARAMETROS_PADRAO,
) -> tuple[list[Path], int]:
    """Lê a entrada, calcula as retenções e exporta o relatório em PDF.

    O cabeçalho (prestador) é montado automaticamente a partir das notas.
    Retorna ``(lista_de_arquivos_gerados, quantidade_de_notas)``.
    """
    notas = ler_entrada(entrada)
    calculadas = calcular_notas(notas, parametros)
    cabecalho = montar_cabecalho(notas)
    gerados = exportar(calculadas, saida, cabecalho)
    return gerados, len(calculadas)
