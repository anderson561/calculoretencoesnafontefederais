"""Motor de cálculo de retenções federais.

Regras de negócio:

- **Só o tomador Pessoa Jurídica (CNPJ) sofre retenção.** Pessoa Física (CPF) e
  notas sem documento nunca retêm (IRRF = CRF = INSS = 0).
- IRRF   = valor_bruto * aliquota_irrf  (dispensa decidida pelo acúmulo por data)
- CRF    = valor_bruto * (PIS + COFINS + CSLL), dispensado se < mínimo
- INSS   = base * aliquota_inss (base limitada ao teto), dispensado se < mínimo
- **Acúmulo de IRRF (sempre ativo):** soma o IRRF das notas do mesmo tomador na
  **mesma data**; se a soma atingir o mínimo (R$ 10,00) retém, senão dispensa.
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
    """Calcula IRRF, CRF e INSS para uma nota, aplicando as regras de negócio.

    Somente tomador Pessoa Jurídica (CNPJ) sofre retenção; qualquer outro tipo
    (CPF ou sem documento) retorna zero. O IRRF é devolvido *bruto* — a dispensa
    do IRRF é decidida no acúmulo por data (:func:`aplicar_dispensa_irrf_acumulada`).
    """
    zero = Decimal("0.00")
    if nota.tipo_tomador != TipoTomador.CNPJ:
        return Retencoes(irrf=zero, crf=zero, inss=zero)

    bruto = Decimal(nota.valor_bruto)
    minimo = parametros.valor_minimo_retencao

    # IRRF bruto (dispensa aplicada depois, no acúmulo por data).
    irrf = _arredondar(bruto * parametros.aliquota_irrf)

    # CRF (PIS/COFINS/CSLL), dispensado se abaixo do mínimo.
    crf = _aplicar_dispensa(_arredondar(bruto * parametros.aliquota_crf), minimo)

    # INSS — base limitada ao teto previdenciário, quando configurado (> 0).
    base_inss = bruto
    if parametros.teto_inss > 0 and base_inss > parametros.teto_inss:
        base_inss = parametros.teto_inss
    inss = _aplicar_dispensa(_arredondar(base_inss * parametros.aliquota_inss), minimo)

    return Retencoes(irrf=irrf, crf=crf, inss=inss)


def _irrf_bruto(nota: Nota, parametros: ParametrosRetencao) -> Decimal:
    """IRRF calculado sobre o valor bruto, sem aplicar a dispensa."""
    return _arredondar(Decimal(nota.valor_bruto) * parametros.aliquota_irrf)


def aplicar_dispensa_irrf_acumulada(
    calculadas: Iterable[NotaCalculada],
    parametros: ParametrosRetencao = PARAMETROS_PADRAO,
) -> list[NotaCalculada]:
    """Aplica a dispensa do IRRF acumulando o imposto por tomador e **mesma data**.

    Regra (sempre ativa): a primeira avaliação é a data — só somam notas do mesmo
    tomador CNPJ emitidas no mesmo dia. Soma o IRRF bruto dessas notas; se o total
    atingir o mínimo (R$ 10,00) mantém o IRRF de cada uma, senão zera todas.
    Notas sem data de emissão são avaliadas isoladamente (uma a uma).

    Só tomador CNPJ é considerado (CPF e sem documento já têm IRRF = 0).
    Modifica os objetos in place e devolve a mesma lista.
    """
    calculadas = list(calculadas)
    minimo = parametros.valor_minimo_retencao
    grupos: dict[tuple, list[NotaCalculada]] = defaultdict(list)
    for idx, nc in enumerate(calculadas):
        if nc.nota.tipo_tomador != TipoTomador.CNPJ:
            continue  # PF e sem documento não retêm
        # 1ª avaliação = mesma data. Sem data -> grupo próprio (não soma com outras).
        data_chave = nc.nota.data_emissao if nc.nota.data_emissao is not None else ("__sem_data__", idx)
        grupos[(nc.nota.documento_tomador, data_chave)].append(nc)

    for grupo in grupos.values():
        acumulado = sum((_irrf_bruto(nc.nota, parametros) for nc in grupo), Decimal("0"))
        dispensar = acumulado < minimo
        for nc in grupo:
            nc.retencoes.irrf = (
                Decimal("0.00") if dispensar else _irrf_bruto(nc.nota, parametros)
            )
    return calculadas
