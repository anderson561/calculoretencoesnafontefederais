from pathlib import Path

from openpyxl import load_workbook

from retencoes.pipeline import processar

CSV = """numero;documento;nome;valor
1001;11.222.333/0001-81;Empresa Alpha Ltda;10000,00
1002;11.222.333/0001-81;Empresa Alpha Ltda;5000,00
1003;111.444.777-35;Joao Silva;3000,00
1004;;Consumidor Final;800,00
"""


def _csv(tmp_path: Path) -> Path:
    entrada = tmp_path / "notas.csv"
    entrada.write_text(CSV, encoding="utf-8")
    return entrada


def test_fluxo_excel(tmp_path: Path):
    saida = tmp_path / "out" / "retencoes.xlsx"
    gerados, qtd = processar(_csv(tmp_path), saida)

    assert qtd == 4
    assert len(gerados) == 1
    assert gerados[0].exists() and gerados[0].suffix == ".xlsx"

    wb = load_workbook(gerados[0])
    assert "Sintético (Tipo)" in wb.sheetnames
    assert "Analítico (Tomador)" in wb.sheetnames


def test_fluxo_pdf(tmp_path: Path):
    saida = tmp_path / "retencoes.pdf"
    gerados, qtd = processar(_csv(tmp_path), saida)

    assert qtd == 4
    assert len(gerados) == 1
    pdf = gerados[0]
    assert pdf.exists() and pdf.suffix == ".pdf"
    # Assinatura de um arquivo PDF válido.
    assert pdf.read_bytes()[:5] == b"%PDF-"


def test_fluxo_ambos(tmp_path: Path):
    saida = tmp_path / "retencoes.xlsx"
    gerados, _ = processar(_csv(tmp_path), saida, formato="ambos")

    sufixos = sorted(g.suffix for g in gerados)
    assert sufixos == [".pdf", ".xlsx"]
    assert all(g.exists() for g in gerados)


def test_diretorio_com_multiplos_arquivos(tmp_path: Path):
    (tmp_path / "a.csv").write_text(CSV, encoding="utf-8")
    (tmp_path / "b.csv").write_text(CSV, encoding="utf-8")
    saida = tmp_path / "retencoes.xlsx"

    _, qtd = processar(tmp_path, saida)
    assert qtd == 8
