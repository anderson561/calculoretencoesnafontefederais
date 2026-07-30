"""Helpers de formatação compartilhados pelos relatórios (Excel e PDF)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from ..models import Cabecalho, TipoTomador

# Texto exibido quando o imposto não foi informado na origem (não confundir
# com R$ 0,00, que significa "informado e dispensado/zero").
NAO_INFORMADO = "-"


def mascarar_documento(doc: str, tipo: TipoTomador) -> str:
    """Aplica a máscara de CNPJ ou CPF; devolve '-' se vazio."""
    if tipo == TipoTomador.CNPJ and len(doc) == 14:
        return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    if tipo == TipoTomador.CPF and len(doc) == 11:
        return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    return doc or "-"


def moeda_br(valor: Optional[Decimal]) -> str:
    """Formata um Decimal como moeda brasileira: 'R$ 1.234,56'.

    ``None`` (imposto não informado na origem) devolve :data:`NAO_INFORMADO`.
    """
    if valor is None:
        return NAO_INFORMADO
    texto = f"{Decimal(valor):,.2f}"  # 1,234.56 (padrão en-US)
    # Troca separadores para o padrão BR.
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def _mascara_cnpj(cnpj: str) -> str:
    doc = "".join(c for c in cnpj if c.isdigit())
    if len(doc) == 14:
        return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    return cnpj


def linhas_cabecalho(cab: Cabecalho | None) -> list[tuple[str, str]]:
    """Monta as linhas (rótulo, valor) do cabeçalho do relatório.

    O prestador é extraído da NFSe; em planilhas fica em branco (linha omitida).
    A data de emissão do relatório é preenchida com a data atual quando ausente.
    """
    cab = cab or Cabecalho()
    linhas: list[tuple[str, str]] = []
    if cab.prestador:
        linhas.append(("Prestador", cab.prestador))
    if cab.cnpj:
        linhas.append(("CNPJ", _mascara_cnpj(cab.cnpj)))
    emissao = cab.data_emissao or date.today().strftime("%d/%m/%Y")
    linhas.append(("Emissão", emissao))
    return linhas
