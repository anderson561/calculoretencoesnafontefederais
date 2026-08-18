"""CLI da Calculadora e Totalizadora de Retenções Federais (NFSe).

Uso:
    python src/main.py -e <entrada> -s <saida.pdf> [opções]

Onde <entrada> é um arquivo (.xml/.csv/.xlsx) ou um diretório com vários deles.
O relatório é sempre gerado em PDF.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permite executar tanto como módulo quanto como script solto (PyInstaller).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from retencoes.config import ParametrosRetencao  # type: ignore
    from retencoes.pipeline import processar  # type: ignore
else:  # pragma: no cover
    from .retencoes.config import ParametrosRetencao
    from .retencoes.pipeline import processar


def montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Totaliza retenções federais (IRRF, CRF, INSS) de NFSe já informadas "
            "no XML/planilha de origem — não aplica alíquota alguma. Mínimo de "
            "dispensa fixo em R$ 10,00 (legislação federal), não configurável."
        ),
    )
    p.add_argument("-e", "--entrada", required=True,
                   help="Arquivo (.xml/.csv/.xlsx) ou diretório com as notas.")
    p.add_argument("-s", "--saida", default="relatorios/retencoes.pdf",
                   help="Caminho do relatório em PDF (padrão: relatorios/retencoes.pdf).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = montar_parser().parse_args(argv)
    entrada = Path(args.entrada)
    if not entrada.exists():
        print(f"[ERRO] Entrada não encontrada: {entrada}", file=sys.stderr)
        return 2

    try:
        gerados, qtd, qtd_substituidas = processar(entrada, args.saida, ParametrosRetencao())
    except Exception as exc:  # noqa: BLE001 — CLI amigável ao usuário final
        print(f"[ERRO] Falha ao processar: {exc}", file=sys.stderr)
        return 1

    print(f"[OK] {qtd} nota(s) processada(s).")
    if qtd_substituidas:
        print(f"[OK] {qtd_substituidas} nota(s) substituída(s) excluída(s) do total (evita duplicidade).")
    for caminho in gerados:
        print(f"[OK] Relatório gerado em: {caminho.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
