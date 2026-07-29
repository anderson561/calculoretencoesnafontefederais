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


def _irrf(notas):
    return {nc.nota.numero: nc.retencoes.irrf for nc in calcular_notas(notas, ParametrosRetencao())}


def test_mesmo_dia_soma_e_retem():
    # 5,00 + 7,00 no mesmo dia = 12,00 (>= 10) -> retém ambas.
    r = _irrf([_nota("1", "333.34"), _nota("2", "466.67")])
    # 333,34*1,5%=5,00 ; 466,67*1,5%=7,00
    assert r["1"] == Decimal("5.00")
    assert r["2"] == Decimal("7.00")


def test_datas_diferentes_nao_somam():
    # 5,00 e 4,00 em dias diferentes -> cada um < 10 -> dispensa (0).
    r = _irrf([
        _nota("1", "333.34", data=date(2026, 7, 10)),
        _nota("2", "266.67", data=date(2026, 7, 11)),  # 4,00
    ])
    assert r["1"] == Decimal("0.00")
    assert r["2"] == Decimal("0.00")


def test_mesmo_dia_acumula_outro_dia_nao():
    r = _irrf([
        _nota("1", "400.00", data=date(2026, 7, 10)),  # 6,00
        _nota("2", "400.00", data=date(2026, 7, 10)),  # 6,00 -> soma 12 retém
        _nota("3", "400.00", data=date(2026, 7, 11)),  # 6,00 sozinho -> dispensa
    ])
    assert r["1"] == Decimal("6.00")
    assert r["2"] == Decimal("6.00")
    assert r["3"] == Decimal("0.00")


def test_nota_individual_acima_do_minimo_mantem():
    r = _irrf([_nota("1", "10000.00")])  # 150,00
    assert r["1"] == Decimal("150.00")


def test_sem_data_avalia_isolada():
    # Sem data: cada nota avaliada sozinha; 6,00 < 10 -> dispensa.
    r = _irrf([_nota("1", "400.00", data=None), _nota("2", "400.00", data=None)])
    assert r["1"] == Decimal("0.00")
    assert r["2"] == Decimal("0.00")


def test_pessoa_fisica_nunca_retem_irrf():
    r = _irrf([_nota("1", "10000.00", doc="11144477735", tipo=TipoTomador.CPF)])
    assert r["1"] == Decimal("0.00")
