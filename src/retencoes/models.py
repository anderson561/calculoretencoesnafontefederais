"""Modelos de domínio do motor de retenções."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class TipoTomador(str, Enum):
    """Classificação do tomador do serviço (RF02)."""

    CNPJ = "CNPJ"
    CPF = "CPF"
    SEM_DOCUMENTO = "SEM_DOCUMENTO"

    @property
    def rotulo(self) -> str:
        return {
            TipoTomador.CNPJ: "Clientes com CNPJ",
            TipoTomador.CPF: "Clientes com CPF",
            TipoTomador.SEM_DOCUMENTO: "Sem CPF / CNPJ",
        }[self]


@dataclass
class Nota:
    """Uma NFSe normalizada, independente da origem (XML ou planilha)."""

    numero: str
    documento_tomador: str  # documento sanitizado (só dígitos) ou ""
    tipo_tomador: TipoTomador
    nome_tomador: Optional[str]
    valor_bruto: Decimal

    # Data de emissão da nota (usada para acumular o IRRF por data).
    data_emissao: Optional[date] = None

    # Prestador do serviço (extraído do XML da NFSe; ausente em planilhas).
    prestador_nome: Optional[str] = None
    prestador_cnpj: Optional[str] = None

    # Valores de retenção JÁ INFORMADOS na origem (XML ou coluna de planilha).
    # ``None`` = não informado (não deve ser calculado); Decimal, inclusive
    # "0.00", = informado explicitamente.
    irrf_informado: Optional[Decimal] = None
    crf_informado: Optional[Decimal] = None
    inss_informado: Optional[Decimal] = None

    # Origem do registro, útil para rastreabilidade e depuração.
    origem: Optional[str] = None

    @property
    def competencia(self) -> Optional[str]:
        """Competência (mês/ano) da nota, no formato 'MM/AAAA'."""
        if self.data_emissao is None:
            return None
        return f"{self.data_emissao.month:02d}/{self.data_emissao.year}"


@dataclass
class Retencoes:
    """Valores de retenção de uma nota.

    Cada campo é ``None`` quando o imposto não foi informado na origem (XML ou
    planilha) — nesse caso nenhum cálculo é feito. Um valor ``Decimal`` (mesmo
    "0.00") indica que o imposto foi informado e, se zero, dispensado.
    """

    irrf: Optional[Decimal]
    crf: Optional[Decimal]
    inss: Optional[Decimal]

    @property
    def total(self) -> Decimal:
        return (self.irrf or Decimal("0.00")) + (self.crf or Decimal("0.00")) + (self.inss or Decimal("0.00"))


@dataclass
class NotaCalculada:
    """Nota acompanhada de suas retenções calculadas."""

    nota: Nota
    retencoes: Retencoes


@dataclass
class Cabecalho:
    """Identificação do prestador exibida no topo dos relatórios.

    O prestador é extraído da NFSe (XML); em planilhas fica em branco.
    ``data_emissao`` vazia é preenchida com a data atual no momento da exportação.
    """

    prestador: str = ""
    cnpj: str = ""
    data_emissao: str = ""  # dd/mm/aaaa
