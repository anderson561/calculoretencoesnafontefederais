from decimal import Decimal

from retencoes.models import Cabecalho, Nota, NotaCalculada, Retencoes, TipoTomador
from retencoes.relatorios.pdf import _linha_cabecalho_markup, exportar_pdf


def test_cabecalho_escapa_caracteres_especiais_do_prestador():
    # Sem escape, "<Filial 2>" seria interpretado como tag e cortado do texto.
    markup = _linha_cabecalho_markup("Prestador", "Comercio <Filial 2> & Cia Ltda")
    assert "&lt;Filial 2&gt;" in markup
    assert "&amp; Cia" in markup
    assert "<Filial 2>" not in markup  # não deve sobrar markup não escapado


def test_exportar_pdf_nao_trava_com_caracteres_especiais(tmp_path):
    cab = Cabecalho(prestador="J & J <Matriz> Ltda", cnpj="11222333000181")
    nota = Nota(numero="1", documento_tomador="11222333000181", tipo_tomador=TipoTomador.CNPJ,
                nome_tomador="Cliente <VIP> & Cia", valor_bruto=Decimal("100"))
    nc = NotaCalculada(nota=nota, retencoes=Retencoes(irrf=Decimal("10"), crf=None, inss=None))

    caminho = exportar_pdf([nc], tmp_path / "retencoes.pdf", cab)
    assert caminho.exists()
    assert caminho.read_bytes()[:5] == b"%PDF-"
