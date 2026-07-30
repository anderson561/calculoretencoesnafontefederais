"""Exportação dos relatórios 1, 2 e 3 para PDF (RF04/RF05) usando reportlab."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..models import Cabecalho, NotaCalculada
from .agregacao import agregar_analitico, agregar_sintetico, agregar_trimestral
from .formatacao import linhas_cabecalho, mascarar_documento, moeda_br

_AZUL = colors.HexColor("#1F4E78")
_CINZA = colors.HexColor("#D9D9D9")
_CINZA_CLARO = colors.HexColor("#F2F2F2")
_ESTILO_NOME = ParagraphStyle("nome_celula", fontName="Helvetica", fontSize=8, leading=10)


def _celula_nome(texto: str) -> Paragraph:
    """Nome/Razão Social como Paragraph, para quebrar linha em vez de vazar da coluna."""
    return Paragraph(escape(texto), _ESTILO_NOME)


def _linha_cabecalho_markup(rotulo: str, valor: str) -> str:
    """Markup do reportlab para uma linha do cabeçalho, com valor escapado.

    ``valor`` vem de dados externos (ex.: razão social do prestador) — sem
    escapar, caracteres como ``<``/``&`` são interpretados como markup pelo
    Paragraph e o texto é silenciosamente cortado/corrompido.
    """
    return f"<b>{escape(rotulo)}:</b> {escape(valor)}"


def _estilo_tabela(n_linhas: int, com_total: bool, col_direita: int = 2) -> TableStyle:
    comandos = [
        ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (col_direita, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _CINZA_CLARO]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if com_total:
        comandos += [
            ("BACKGROUND", (0, n_linhas - 1), (-1, n_linhas - 1), _CINZA),
            ("FONTNAME", (0, n_linhas - 1), (-1, n_linhas - 1), "Helvetica-Bold"),
        ]
    return TableStyle(comandos)


def _tabela_sintetico(notas: list[NotaCalculada]) -> Table:
    cab = ["Categoria", "Qtd.", "Valor Bruto", "Total IRRF", "Total CRF", "Total INSS"]
    dados = [cab]
    tot = {"qtd": 0, "b": Decimal("0"), "i": Decimal("0"), "c": Decimal("0"), "n": Decimal("0")}
    for ls in agregar_sintetico(notas):
        dados.append([
            ls.categoria.rotulo, str(ls.qtd_notas), moeda_br(ls.valor_bruto),
            moeda_br(ls.total_irrf), moeda_br(ls.total_crf), moeda_br(ls.total_inss),
        ])
        tot["qtd"] += ls.qtd_notas
        tot["b"] += ls.valor_bruto
        tot["i"] += ls.total_irrf
        tot["c"] += ls.total_crf
        tot["n"] += ls.total_inss
    dados.append([
        "TOTAL GERAL", str(tot["qtd"]), moeda_br(tot["b"]),
        moeda_br(tot["i"]), moeda_br(tot["c"]), moeda_br(tot["n"]),
    ])
    larguras = [55 * mm, 18 * mm, 35 * mm, 30 * mm, 30 * mm, 30 * mm]
    t = Table(dados, colWidths=larguras, repeatRows=1)
    t.setStyle(_estilo_tabela(len(dados), com_total=True))
    return t


_LARGURAS_ANALITICO = [30 * mm, 24 * mm, 24 * mm, 42 * mm, 10 * mm,
                       27 * mm, 24 * mm, 24 * mm, 24 * mm]


def _tabela_analitico(linhas) -> Table:
    """Uma linha por nota, com subtotal por tomador quando há mais de uma."""
    cab = ["Documento", "Número NF", "Data", "Nome / Razão Social", "Qtd.",
           "Valor Bruto", "IRRF", "CRF", "INSS"]
    dados = [cab]
    linhas_subtotal: list[int] = []
    if not linhas:
        dados.append(["(sem registros)"] + [""] * 8)
    else:
        for la in linhas:
            doc_fmt = mascarar_documento(la.documento, la.tipo)
            for item in la.itens_ordenados:
                dados.append([
                    doc_fmt, item.numero, item.data_fmt, _celula_nome(la.nome or "-"), "1",
                    moeda_br(item.valor_bruto), moeda_br(item.irrf),
                    moeda_br(item.crf), moeda_br(item.inss),
                ])
            if la.qtd_notas > 1:
                dados.append([
                    "", "", "", _celula_nome(f"Subtotal — {la.nome or doc_fmt}"), str(la.qtd_notas),
                    moeda_br(la.valor_bruto), moeda_br(la.total_irrf),
                    moeda_br(la.total_crf), moeda_br(la.total_inss),
                ])
                linhas_subtotal.append(len(dados) - 1)
    t = Table(dados, colWidths=_LARGURAS_ANALITICO, repeatRows=1)
    estilo = _estilo_tabela(len(dados), com_total=False, col_direita=4)
    for linha_idx in linhas_subtotal:
        estilo.add("BACKGROUND", (0, linha_idx), (-1, linha_idx), _CINZA_CLARO)
        estilo.add("FONTNAME", (0, linha_idx), (-1, linha_idx), "Helvetica-Oblique")
    t.setStyle(estilo)
    return t


def _tabela_total_analitico(total) -> Table:
    """Linha única de TOTAL GERAL, somando os três blocos do Relatório 2."""
    dados = [[
        "TOTAL GERAL", "", "", "", str(total.qtd_notas), moeda_br(total.valor_bruto),
        moeda_br(total.total_irrf), moeda_br(total.total_crf), moeda_br(total.total_inss),
    ]]
    t = Table(dados, colWidths=_LARGURAS_ANALITICO)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _CINZA),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _tabela_trimestral(notas: list[NotaCalculada]) -> Table:
    cab = ["Trimestre", "Qtd.", "Valor Bruto", "Total IRRF", "Total CRF", "Total INSS"]
    dados = [cab]
    tot = {"qtd": 0, "b": Decimal("0"), "i": Decimal("0"), "c": Decimal("0"), "n": Decimal("0")}
    linhas = agregar_trimestral(notas)
    if not linhas:
        dados.append(["(sem registros)"] + [""] * 5)
    for lt in linhas:
        dados.append([
            lt.rotulo, str(lt.qtd_notas), moeda_br(lt.valor_bruto),
            moeda_br(lt.total_irrf), moeda_br(lt.total_crf), moeda_br(lt.total_inss),
        ])
        tot["qtd"] += lt.qtd_notas
        tot["b"] += lt.valor_bruto
        tot["i"] += lt.total_irrf
        tot["c"] += lt.total_crf
        tot["n"] += lt.total_inss
    dados.append([
        "TOTAL GERAL", str(tot["qtd"]), moeda_br(tot["b"]),
        moeda_br(tot["i"]), moeda_br(tot["c"]), moeda_br(tot["n"]),
    ])
    larguras = [55 * mm, 18 * mm, 35 * mm, 30 * mm, 30 * mm, 30 * mm]
    t = Table(dados, colWidths=larguras, repeatRows=1)
    t.setStyle(_estilo_tabela(len(dados), com_total=True))
    return t


def exportar_pdf(
    notas: list[NotaCalculada], caminho: str | Path, cabecalho: Cabecalho | None = None
) -> Path:
    """Gera um PDF (paisagem A4) com os relatórios sintético, analítico e trimestral."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(caminho), pagesize=landscape(A4),
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title="Retenções Federais (NFSe)",
    )
    estilos = getSampleStyleSheet()
    h1 = estilos["Heading1"]
    h1.textColor = _AZUL
    h2 = estilos["Heading2"]
    h2.textColor = _AZUL
    info = estilos["Normal"].clone("info")
    info.fontSize = 9
    info.textColor = colors.HexColor("#404040")

    elementos: list = [Paragraph("Retenções Federais sobre NFSe", h1)]
    for rotulo, valor in linhas_cabecalho(cabecalho):
        elementos.append(Paragraph(_linha_cabecalho_markup(rotulo, valor), info))
    elementos += [
        Spacer(1, 4 * mm),
        Paragraph("Relatório 1 — Totalizador por Tipo de Documento", h2),
        Spacer(1, 2 * mm),
        _tabela_sintetico(notas),
        Spacer(1, 8 * mm),
        Paragraph("Relatório 2 — Totalizador Analítico por Tomador", h2),
        Spacer(1, 2 * mm),
    ]

    rel = agregar_analitico(notas)
    for titulo, dados in (
        ("Bloco 1 — Resumo por CNPJ", rel.por_cnpj),
        ("Bloco 2 — Resumo por CPF", rel.por_cpf),
        ("Bloco 3 — Sem CPF ou CNPJ", rel.sem_documento),
    ):
        elementos.append(Paragraph(titulo, estilos["Heading3"]))
        elementos.append(Spacer(1, 1 * mm))
        elementos.append(_tabela_analitico(dados))
        elementos.append(Spacer(1, 5 * mm))

    elementos.append(_tabela_total_analitico(rel.total_geral()))

    elementos += [
        Spacer(1, 8 * mm),
        Paragraph("Relatório 3 — Totalizador Trimestral", h2),
        Spacer(1, 2 * mm),
        _tabela_trimestral(notas),
    ]

    doc.build(elementos)
    return caminho
