"""Agregação dos totais para os relatórios sintético e analítico.

Lógica pura (sem dependência de bibliotecas de saída), portanto facilmente
testável.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable

from ..models import NotaCalculada, TipoTomador

_ZERO = Decimal("0.00")


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
        self.total_irrf += nc.retencoes.irrf
        self.total_crf += nc.retencoes.crf
        self.total_inss += nc.retencoes.inss


@dataclass
class LinhaAnalitica:
    """Uma linha do Relatório 2 (por tomador individual)."""

    documento: str
    nome: str | None
    tipo: TipoTomador
    qtd_notas: int = 0
    valor_bruto: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_irrf: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_crf: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_inss: Decimal = field(default_factory=lambda: Decimal("0.00"))
    # Pares (número da nota, data de emissão formatada) para exibição.
    itens: list[tuple[str, str]] = field(default_factory=list)

    def acumular(self, nc: NotaCalculada) -> None:
        self.qtd_notas += 1
        self.valor_bruto += nc.nota.valor_bruto
        self.total_irrf += nc.retencoes.irrf
        self.total_crf += nc.retencoes.crf
        self.total_inss += nc.retencoes.inss
        data_fmt = nc.nota.data_emissao.strftime("%d/%m/%Y") if nc.nota.data_emissao else "-"
        self.itens.append((str(nc.nota.numero), data_fmt))
        if not self.nome and nc.nota.nome_tomador:
            self.nome = nc.nota.nome_tomador

    @property
    def _itens_ordenados(self) -> list[tuple[str, str]]:
        return sorted(self.itens, key=lambda it: (len(it[0]), it[0]))

    @property
    def numeros_fmt(self) -> str:
        """Números das notas do tomador, ordenados e unidos por vírgula."""
        return ", ".join(n for n, _ in self._itens_ordenados)

    @property
    def datas_fmt(self) -> str:
        """Datas de emissão das notas, na mesma ordem dos números."""
        return ", ".join(d for _, d in self._itens_ordenados)


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
