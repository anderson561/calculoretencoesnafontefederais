"""Parâmetros de cálculo das retenções federais.

Todos os valores são *defaults* e podem ser sobrescritos pelo usuário.

AVISO FISCAL: as alíquotas e regras abaixo refletem o descrito no PRD e devem
ser validadas por profissional fiscal contra a legislação vigente. O software
apenas aplica os parâmetros configurados — não constitui aconselhamento fiscal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


def _d(valor: str) -> Decimal:
    return Decimal(valor)


@dataclass(frozen=True)
class ParametrosRetencao:
    """Configuração parametrizável do motor de cálculo.

    As alíquotas são expressas como fração (ex.: 0.015 == 1,5%).
    """

    # IRRF — 1,5% padrão (RF03). Alguns serviços usam 1%.
    aliquota_irrf: Decimal = field(default_factory=lambda: _d("0.015"))

    # CRF (Contribuição unificada) = PIS + COFINS + CSLL = 4,65%
    aliquota_pis: Decimal = field(default_factory=lambda: _d("0.0065"))
    aliquota_cofins: Decimal = field(default_factory=lambda: _d("0.03"))
    aliquota_csll: Decimal = field(default_factory=lambda: _d("0.01"))

    # INSS — 11% padrão sobre o valor bruto (retenção previdenciária)
    aliquota_inss: Decimal = field(default_factory=lambda: _d("0.11"))

    # Teto previdenciário aplicável ao INSS (0 = sem teto). Ajustável por ano.
    teto_inss: Decimal = field(default_factory=lambda: _d("0"))

    # Regra de dispensa: retenção inferior a este valor é dispensada/zerada.
    # (legislação federal: dispensa de IRRF igual ou inferior a R$ 10,00)
    valor_minimo_retencao: Decimal = field(default_factory=lambda: _d("10.00"))

    @property
    def aliquota_crf(self) -> Decimal:
        """Alíquota combinada de PIS + COFINS + CSLL."""
        return self.aliquota_pis + self.aliquota_cofins + self.aliquota_csll


# Instância padrão pronta para uso.
PARAMETROS_PADRAO = ParametrosRetencao()
