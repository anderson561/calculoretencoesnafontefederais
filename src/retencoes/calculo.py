"""Motor de cálculo de retenções federais (RF03).

Regras aplicadas (todas parametrizáveis via :class:`ParametrosRetencao`):

- IRRF   = valor_bruto * aliquota_irrf
- CRF    = valor_bruto * (PIS + COFINS + CSLL)   (isento para PF, se configurado)
- INSS   = base * aliquota_inss  (base limitada ao teto, se configurado)
- Dispensa: cada tributo cujo valor calculado seja inferior a
  ``valor_minimo_retencao`` é zerado.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from .config import PARAMETROS_PADRAO, ParametrosRetencao
from .models import Nota, NotaCalculada, Retencoes, TipoTomador

_CENTAVOS = Decimal("0.01")


def _arredondar(valor: Decimal) -> Decimal:
    """Arredonda para 2 casas (meio-para-cima)."""
    return valor.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)


def _aplicar_dispensa(valor: Decimal, minimo: Decimal) -> Decimal:
    """Zera o tributo se o valor for inferior ao mínimo de retenção."""
    return valor if valor >= minimo else Decimal("0.00")


def calcular_retencoes(
    nota: Nota,
    parametros: ParametrosRetencao = PARAMETROS_PADRAO,
) -> Retencoes:
    """Calcula IRRF, CRF e INSS para uma nota, aplicando as regras de negócio."""
    bruto = Decimal(nota.valor_bruto)

    # IRRF
    irrf = _arredondar(bruto * parametros.aliquota_irrf)

    # CRF (PIS/COFINS/CSLL) — isento para Pessoa Física, se configurado.
    if nota.tipo_tomador == TipoTomador.CPF and parametros.crf_isento_para_pf:
        crf = Decimal("0.00")
    else:
        crf = _arredondar(bruto * parametros.aliquota_crf)

    # INSS — base limitada ao teto previdenciário, quando configurado (> 0).
    base_inss = bruto
    if parametros.teto_inss > 0 and base_inss > parametros.teto_inss:
        base_inss = parametros.teto_inss
    inss = _arredondar(base_inss * parametros.aliquota_inss)

    # Regra de dispensa por tributo.
    minimo = parametros.valor_minimo_retencao
    return Retencoes(
        irrf=_aplicar_dispensa(irrf, minimo),
        crf=_aplicar_dispensa(crf, minimo),
        inss=_aplicar_dispensa(inss, minimo),
    )


def _irrf_bruto(nota: Nota, parametros: ParametrosRetencao) -> Decimal:
    """IRRF calculado sobre o valor bruto, sem aplicar a dispensa."""
    return _arredondar(Decimal(nota.valor_bruto) * parametros.aliquota_irrf)


def aplicar_dispensa_irrf_acumulada(
    calculadas: Iterable[NotaCalculada],
    parametros: ParametrosRetencao = PARAMETROS_PADRAO,
) -> list[NotaCalculada]:
    """Reavalia a dispensa do IRRF acumulando o imposto por tomador e data.

    Só acumula notas do mesmo tomador identificado (CNPJ/CPF) emitidas na **mesma
    data** (dia/mês/ano). Para cada par (tomador, data), soma o IRRF *bruto*; se o
    total ficar abaixo do mínimo, zera o IRRF de todas; caso contrário, mantém o
    IRRF bruto de cada nota. Notas sem documento ou **sem data de emissão** não
    acumulam e preservam a dispensa nota a nota já calculada.

    Modifica os objetos in place e devolve a mesma lista.
    """
    calculadas = list(calculadas)
    if not parametros.irrf_dispensa_por_acumulo:
        return calculadas

    minimo = parametros.valor_minimo_retencao
    grupos: dict[tuple, list[NotaCalculada]] = defaultdict(list)
    for nc in calculadas:
        if nc.nota.tipo_tomador == TipoTomador.SEM_DOCUMENTO:
            continue  # sem beneficiário identificado: não acumula
        if nc.nota.data_emissao is None:
            continue  # sem data: não há como aferir "mesmo dia" -> nota a nota
        chave = (nc.nota.tipo_tomador, nc.nota.documento_tomador, nc.nota.data_emissao)
        grupos[chave].append(nc)

    for grupo in grupos.values():
        acumulado = sum((_irrf_bruto(nc.nota, parametros) for nc in grupo), Decimal("0"))
        dispensar = acumulado < minimo
        for nc in grupo:
            nc.retencoes.irrf = (
                Decimal("0.00") if dispensar else _irrf_bruto(nc.nota, parametros)
            )
    return calculadas
