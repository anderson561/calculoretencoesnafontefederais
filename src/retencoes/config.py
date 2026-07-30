"""Parâmetros de cálculo das retenções federais.

AVISO FISCAL: o software não aplica alíquota alguma — ele apenas totaliza os
valores de retenção já informados na origem (XML da NFSe ou coluna da
planilha). O único parâmetro configurável é o valor mínimo de dispensa.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


def _d(valor: str) -> Decimal:
    return Decimal(valor)


@dataclass(frozen=True)
class ParametrosRetencao:
    """Configuração parametrizável do motor de totalização."""

    # Regra de dispensa: retenção informada inferior a este valor é zerada.
    # (legislação federal: dispensa de IRRF igual ou inferior a R$ 10,00)
    valor_minimo_retencao: Decimal = field(default_factory=lambda: _d("10.00"))


# Instância padrão pronta para uso.
PARAMETROS_PADRAO = ParametrosRetencao()
