"""Agregação dos totais para os relatórios sintético, analítico e trimestral.

Lógica pura (sem dependência de bibliotecas de saída), portanto facilmente
testável.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, Optional

from ..datas import trimestre_chave, trimestre_rotulo
from ..models import NotaCalculada, TipoTomador

_ZERO = Decimal("0.00")


def _ou_zero(valor: Optional[Decimal]) -> Decimal:
    return valor if valor is not None else _ZERO


@dataclass
class LinhaSintetica:
    """Uma linha do Relatório 1 (por tipo de documento)."""

    categoria: TipoTomador
    qtd_notas: int = 0
    valor_bruto: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_irrf: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_crf: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_inss: Decimal = field(default_factory=lambda: Decimal("0.00"))

    def acumular(self, nc: NotaCalculada) -> None:
        self.qtd_notas += 1
        self.valor_bruto += nc.nota.valor_bruto
        self.total_irrf += _ou_zero(nc.retencoes.irrf)
        self.total_crf += _ou_zero(nc.retencoes.crf)
        self.total_inss += _ou_zero(nc.retencoes.inss)


@dataclass
class ItemAnalitico:
    """Uma nota individual dentro do bloco do tomador (Relatório 2)."""

    numero: str
    data_fmt: str
    valor_bruto: Decimal
    irrf: Optional[Decimal]
    crf: Optional[Decimal]
    inss: Optional[Decimal]


@dataclass
class LinhaAnalitica:
    """Um tomador do Relatório 2, com o subtotal e as notas individuais."""

    documento: str
    nome: str | None
    tipo: TipoTomador
    qtd_notas: int = 0
    valor_bruto: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_irrf: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_crf: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_inss: Decimal = field(default_factory=lambda: Decimal("0.00"))
    itens: list[ItemAnalitico] = field(default_factory=list)

    def acumular(self, nc: NotaCalculada) -> None:
        self.qtd_notas += 1
        self.valor_bruto += nc.nota.valor_bruto
        self.total_irrf += _ou_zero(nc.retencoes.irrf)
        self.total_crf += _ou_zero(nc.retencoes.crf)
        self.total_inss += _ou_zero(nc.retencoes.inss)
        data_fmt = nc.nota.data_emissao.strftime("%d/%m/%Y") if nc.nota.data_emissao else "-"
        self.itens.append(
            ItemAnalitico(
                numero=str(nc.nota.numero),
                data_fmt=data_fmt,
                valor_bruto=nc.nota.valor_bruto,
                irrf=nc.retencoes.irrf,
                crf=nc.retencoes.crf,
                inss=nc.retencoes.inss,
            )
        )
        if not self.nome and nc.nota.nome_tomador:
            self.nome = nc.nota.nome_tomador

    @property
    def itens_ordenados(self) -> list[ItemAnalitico]:
        return sorted(self.itens, key=lambda it: (len(it.numero), it.numero))


@dataclass
class TotalAnalitico:
    """Somatório geral dos três blocos do Relatório 2."""

    qtd_notas: int = 0
    valor_bruto: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_irrf: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_crf: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_inss: Decimal = field(default_factory=lambda: Decimal("0.00"))


@dataclass
class RelatorioAnalitico:
    """Relatório 2 dividido nos três blocos (CNPJ, CPF, sem documento)."""

    por_cnpj: list[LinhaAnalitica] = field(default_factory=list)
    por_cpf: list[LinhaAnalitica] = field(default_factory=list)
    sem_documento: list[LinhaAnalitica] = field(default_factory=list)

    def total_geral(self) -> TotalAnalitico:
        """Soma os três blocos em um total geral."""
        total = TotalAnalitico()
        for linha in (*self.por_cnpj, *self.por_cpf, *self.sem_documento):
            total.qtd_notas += linha.qtd_notas
            total.valor_bruto += linha.valor_bruto
            total.total_irrf += linha.total_irrf
            total.total_crf += linha.total_crf
            total.total_inss += linha.total_inss
        return total


@dataclass
class LinhaTrimestral:
    """Uma linha do Relatório 3 (totais por trimestre civil)."""

    rotulo: str
    chave: tuple[int, int]
    qtd_notas: int = 0
    valor_bruto: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_irrf: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_crf: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_inss: Decimal = field(default_factory=lambda: Decimal("0.00"))

    def acumular(self, nc: NotaCalculada) -> None:
        self.qtd_notas += 1
        self.valor_bruto += nc.nota.valor_bruto
        self.total_irrf += _ou_zero(nc.retencoes.irrf)
        self.total_crf += _ou_zero(nc.retencoes.crf)
        self.total_inss += _ou_zero(nc.retencoes.inss)


def agregar_sintetico(notas: Iterable[NotaCalculada]) -> list[LinhaSintetica]:
    """Relatório 1: totais por tipo de documento (RF04)."""
    linhas = {tipo: LinhaSintetica(categoria=tipo) for tipo in TipoTomador}
    for nc in notas:
        linhas[nc.nota.tipo_tomador].acumular(nc)
    # Ordem fixa: CNPJ, CPF, SEM_DOCUMENTO.
    return [linhas[t] for t in (TipoTomador.CNPJ, TipoTomador.CPF, TipoTomador.SEM_DOCUMENTO)]


def agregar_analitico(notas: Iterable[NotaCalculada]) -> RelatorioAnalitico:
    """Relatório 2: totais por tomador individual (RF05)."""
    grupos: dict[tuple[TipoTomador, str], LinhaAnalitica] = {}
    for nc in notas:
        tipo = nc.nota.tipo_tomador
        # Sem documento é consolidado em uma única linha.
        chave_doc = nc.nota.documento_tomador if tipo != TipoTomador.SEM_DOCUMENTO else ""
        chave = (tipo, chave_doc)
        linha = grupos.get(chave)
        if linha is None:
            linha = LinhaAnalitica(documento=chave_doc, nome=nc.nota.nome_tomador, tipo=tipo)
            grupos[chave] = linha
        linha.acumular(nc)

    relatorio = RelatorioAnalitico()
    for (tipo, _), linha in sorted(grupos.items(), key=lambda kv: (kv[0][0].value, kv[0][1])):
        if tipo == TipoTomador.CNPJ:
            relatorio.por_cnpj.append(linha)
        elif tipo == TipoTomador.CPF:
            relatorio.por_cpf.append(linha)
        else:
            relatorio.sem_documento.append(linha)
    return relatorio


def agregar_trimestral(notas: Iterable[NotaCalculada]) -> list[LinhaTrimestral]:
    """Relatório 3: totais por trimestre civil (soma a cada 3 meses)."""
    grupos: dict[tuple[int, int], LinhaTrimestral] = {}
    for nc in notas:
        chave = trimestre_chave(nc.nota.data_emissao)
        linha = grupos.get(chave)
        if linha is None:
            linha = LinhaTrimestral(rotulo=trimestre_rotulo(nc.nota.data_emissao), chave=chave)
            grupos[chave] = linha
        linha.acumular(nc)
    return [grupos[chave] for chave in sorted(grupos)]
