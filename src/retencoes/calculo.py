"""Motor de totalização de retenções federais.

Regras de negócio:

- **Só o tomador Pessoa Jurídica (CNPJ) sofre retenção.** Pessoa Física (CPF) e
  notas sem documento nunca retêm (IRRF = CRF = INSS = 0).
- **O software não calcula imposto por alíquota.** Ele só totaliza o que já
  veio informado na origem (XML da NFSe ou coluna da planilha). Se um imposto
  não foi informado, o campo fica ``None`` (não calculado) — não é zero.
- CRF e INSS informados são dispensados (zerados) se abaixo do valor mínimo.
- **Acúmulo de IRRF (sempre ativo):** soma o IRRF informado das notas do mesmo
  tomador na **mesma data**; se a soma atingir o mínimo (R$ 10,00) mantém o
  valor informado de cada nota, senão dispensa (zera) todas as notas do grupo
  que tinham IRRF informado.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Optional

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
    """Totaliza IRRF, CRF e INSS de uma nota a partir do que já foi informado.

    Somente tomador Pessoa Jurídica (CNPJ) sofre retenção; qualquer outro tipo
    (CPF ou sem documento) retorna zero nos três tributos. Para o tomador
    CNPJ, cada tributo só é preenchido se a nota trouxe o valor informado
    (:attr:`Nota.irrf_informado`, ``crf_informado``, ``inss_informado``); caso
    contrário o campo fica ``None`` — nenhum cálculo por alíquota é feito.
    O IRRF informado é devolvido *bruto* — a dispensa do IRRF é decidida no
    acúmulo por data (:func:`aplicar_dispensa_irrf_acumulada`).
    """
    zero = Decimal("0.00")
    if nota.tipo_tomador != TipoTomador.CNPJ:
        return Retencoes(irrf=zero, crf=zero, inss=zero)

    minimo = parametros.valor_minimo_retencao

    irrf: Optional[Decimal] = (
        _arredondar(nota.irrf_informado) if nota.irrf_informado is not None else None
    )
    crf: Optional[Decimal] = (
        _aplicar_dispensa(_arredondar(nota.crf_informado), minimo)
        if nota.crf_informado is not None else None
    )
    inss: Optional[Decimal] = (
        _aplicar_dispensa(_arredondar(nota.inss_informado), minimo)
        if nota.inss_informado is not None else None
    )

    return Retencoes(irrf=irrf, crf=crf, inss=inss)


def aplicar_dispensa_irrf_acumulada(
    calculadas: Iterable[NotaCalculada],
    parametros: ParametrosRetencao = PARAMETROS_PADRAO,
) -> list[NotaCalculada]:
    """Aplica a dispensa do IRRF acumulando o imposto informado por tomador e
    **mesma data**.

    Regra (sempre ativa): a primeira avaliação é a data — só somam notas do
    mesmo tomador CNPJ emitidas no mesmo dia, e apenas as que trouxeram IRRF
    informado. Soma o IRRF informado dessas notas; se o total atingir o
    mínimo (R$ 10,00), mantém o IRRF informado de cada uma, senão zera todas.
    Notas sem IRRF informado permanecem ``None`` (não calculado), independente
    do grupo. Notas sem data de emissão são avaliadas isoladamente.

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
        acumulado = sum(
            (_arredondar(nc.nota.irrf_informado) for nc in grupo if nc.nota.irrf_informado is not None),
            Decimal("0"),
        )
        dispensar = acumulado < minimo
        for nc in grupo:
            if nc.nota.irrf_informado is None:
                nc.retencoes.irrf = None
            else:
                nc.retencoes.irrf = (
                    Decimal("0.00") if dispensar else _arredondar(nc.nota.irrf_informado)
                )
    return calculadas
