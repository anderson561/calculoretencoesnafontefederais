"""CLI da Calculadora e Totalizadora de Retenções Federais (NFSe).

Uso:
    python src/main.py -e <entrada> -s <saida.xlsx> [opções]

Onde <entrada> é um arquivo (.xml/.csv/.xlsx) ou um diretório com vários deles.
"""
from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

# Permite executar tanto como módulo quanto como script solto (PyInstaller).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from retencoes.config import ParametrosRetencao  # type: ignore
    from retencoes.pipeline import processar  # type: ignore
else:  # pragma: no cover
    from .retencoes.config import ParametrosRetencao
    from .retencoes.pipeline import processar


def _construir_parametros(args: argparse.Namespace) -> ParametrosRetencao:
    padrao = ParametrosRetencao()
    return ParametrosRetencao(
        aliquota_irrf=Decimal(str(args.irrf)) if args.irrf is not None else padrao.aliquota_irrf,
        aliquota_inss=Decimal(str(args.inss)) if args.inss is not None else padrao.aliquota_inss,
        valor_minimo_retencao=(
            Decimal(str(args.minimo)) if args.minimo is not None
            else padrao.valor_minimo_retencao
        ),
        teto_inss=Decimal(str(args.teto_inss)) if args.teto_inss is not None else padrao.teto_inss,
    )


def montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Calcula e totaliza retenções federais (IRRF, CRF, INSS) de NFSe.",
    )
    p.add_argument("-e", "--entrada", required=True,
                   help="Arquivo (.xml/.csv/.xlsx) ou diretório com as notas.")
    p.add_argument("-s", "--saida", default="relatorios/retencoes.xlsx",
                   help="Caminho base do relatório (padrão: relatorios/retencoes.xlsx).")
    p.add_argument("-f", "--formato", choices=("auto", "excel", "pdf", "ambos"),
                   default="auto",
                   help="Formato de saída. 'auto' deduz pela extensão de --saida.")
    p.add_argument("--irrf", type=float, help="Alíquota de IRRF em fração (ex.: 0.015).")
    p.add_argument("--inss", type=float, help="Alíquota de INSS em fração (ex.: 0.11).")
    p.add_argument("--minimo", type=float,
                   help="Valor mínimo de retenção; abaixo disso é dispensado (padrão 10.00).")
    p.add_argument("--teto-inss", type=float, dest="teto_inss",
                   help="Teto da base de INSS (0 = sem teto).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = montar_parser().parse_args(argv)
    entrada = Path(args.entrada)
    if not entrada.exists():
        print(f"[ERRO] Entrada não encontrada: {entrada}", file=sys.stderr)
        return 2

    parametros = _construir_parametros(args)
    try:
        gerados, qtd = processar(entrada, args.saida, parametros, args.formato)
    except Exception as exc:  # noqa: BLE001 — CLI amigável ao usuário final
        print(f"[ERRO] Falha ao processar: {exc}", file=sys.stderr)
        return 1

    print(f"[OK] {qtd} nota(s) processada(s).")
    for caminho in gerados:
        print(f"[OK] Relatório gerado em: {caminho.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
