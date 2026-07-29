from datetime import date
from decimal import Decimal

from retencoes.config import ParametrosRetencao
from retencoes.models import Nota, TipoTomador
from retencoes.pipeline import calcular_notas

CNPJ = "11222333000181"
DIA = date(2026, 7, 10)


def _nota(numero, valor, doc=CNPJ, tipo=TipoTomador.CNPJ, data=DIA):
    return Nota(numero=numero, documento_tomador=doc, tipo_tomador=tipo,
               nome_tomador="Cliente", valor_bruto=Decimal(valor), data_emissao=data)


def test_acumulo_restaura_irrf_no_mesmo_dia():
    # Duas notas de R$400 na MESMA data -> IRRF 6,00 cada (soma 12 >= 10 -> mantém).
    notas = [_nota("1", "400.00"), _nota("2", "400.00")]
    calc = calcular_notas(notas, ParametrosRetencao())
    assert [nc.retencoes.irrf for nc in calc] == [Decimal("6.00"), Decimal("6.00")]


def test_acumulo_dispensa_quando_soma_do_dia_fica_abaixo_do_minimo():
    # Nota única de R$300 -> IRRF 4,50 (< 10). Acumulado do dia < 10 -> dispensa.
    calc = calcular_notas([_nota("1", "300.00")], ParametrosRetencao())
    assert calc[0].retencoes.irrf == Decimal("0.00")


def test_datas_diferentes_nao_acumulam():
    # Mesmo CNPJ, R$400 em dias diferentes: cada dia sozinho (6 < 10) -> zerado.
    notas = [
        _nota("1", "400.00", data=date(2026, 7, 10)),
        _nota("2", "400.00", data=date(2026, 7, 11)),
    ]
    calc = calcular_notas(notas, ParametrosRetencao())
    assert [nc.retencoes.irrf for nc in calc] == [Decimal("0.00"), Decimal("0.00")]


def test_mesmo_dia_acumula_mas_outro_dia_nao():
    notas = [
        _nota("1", "400.00", data=date(2026, 7, 10)),
        _nota("2", "400.00", data=date(2026, 7, 10)),
        _nota("3", "400.00", data=date(2026, 7, 11)),
    ]
    calc = {nc.nota.numero: nc.retencoes.irrf for nc in calcular_notas(notas, ParametrosRetencao())}
    assert calc["1"] == Decimal("6.00")
    assert calc["2"] == Decimal("6.00")
    assert calc["3"] == Decimal("0.00")


def test_sem_data_nao_acumula():
    # Sem data de emissão: não acumula -> dispensa nota a nota (6 < 10 -> 0).
    notas = [_nota("1", "400.00", data=None), _nota("2", "400.00", data=None)]
    calc = calcular_notas(notas, ParametrosRetencao())
    assert [nc.retencoes.irrf for nc in calc] == [Decimal("0.00"), Decimal("0.00")]


def test_sem_acumulo_dispensa_nota_a_nota():
    params = ParametrosRetencao(irrf_dispensa_por_acumulo=False)
    calc = calcular_notas([_nota("1", "400.00"), _nota("2", "400.00")], params)
    assert [nc.retencoes.irrf for nc in calc] == [Decimal("0.00"), Decimal("0.00")]


def test_sem_documento_nao_acumula():
    notas = [
        _nota("1", "400.00", doc="", tipo=TipoTomador.SEM_DOCUMENTO),
        _nota("2", "400.00", doc="", tipo=TipoTomador.SEM_DOCUMENTO),
    ]
    calc = calcular_notas(notas, ParametrosRetencao())
    assert [nc.retencoes.irrf for nc in calc] == [Decimal("0.00"), Decimal("0.00")]
