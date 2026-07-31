"""Orquestra o fluxo completo: ingestão -> cálculo -> relatório (PDF)."""
from __future__ import annotations

from pathlib import Path

from .calculo import aplicar_dispensa_irrf_acumulada, calcular_retencoes
from .config import PARAMETROS_PADRAO, ParametrosRetencao
from .ingestao import ler_entrada
from .models import Cabecalho, Nota, NotaCalculada
from .relatorios import exportar_pdf


def remover_notas_substituidas(notas: list[Nota]) -> tuple[list[Nota], list[Nota]]:
    """Exclui notas que foram substituídas por outra nota do mesmo prestador.

    Algumas prefeituras reemitem a NFSe (ex.: ABRASF `<NfseSubstituida>`)
    indicando o número da nota original que ela substitui. Se ambas as notas
    (a original e a substituta) estiverem no mesmo lote de entrada, a
    original deve ser excluída do total — senão a retenção seria contada em
    duplicidade. Retorna ``(notas_mantidas, notas_excluidas)``.
    """
    substituidas = {
        (n.prestador_cnpj, n.numero_substituida)
        for n in notas
        if n.numero_substituida
    }
    mantidas: list[Nota] = []
    excluidas: list[Nota] = []
    for n in notas:
        if (n.prestador_cnpj, n.numero) in substituidas:
            excluidas.append(n)
        else:
            mantidas.append(n)
    return mantidas, excluidas


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
) -> tuple[list[Path], int, int]:
    """Lê a entrada, calcula as retenções e exporta o relatório em PDF.

    O cabeçalho (prestador) é montado automaticamente a partir das notas.
    Retorna ``(lista_de_arquivos_gerados, quantidade_de_notas, quantidade_de_notas_substituidas_excluidas)``.
    """
    todas_as_notas = ler_entrada(entrada)
    notas, substituidas = remover_notas_substituidas(todas_as_notas)
    calculadas = calcular_notas(notas, parametros)
    cabecalho = montar_cabecalho(notas)
    gerados = exportar(calculadas, saida, cabecalho)
    return gerados, len(calculadas), len(substituidas)
