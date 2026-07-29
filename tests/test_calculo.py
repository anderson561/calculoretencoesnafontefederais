from decimal import Decimal

from retencoes.calculo import calcular_retencoes
from retencoes.config import ParametrosRetencao
from retencoes.models import Nota, TipoTomador


def _nota(valor, tipo=TipoTomador.CNPJ):
    return Nota(
        numero="1",
        documento_tomador="11222333000181",
        tipo_tomador=tipo,
        nome_tomador="Teste",
        valor_bruto=Decimal(str(valor)),
    )


def test_calculo_cnpj_valores_default():
    # 10.000,00 -> IRRF 1,5% = 150 ; CRF 4,65% = 465 ; INSS 11% = 1100
    r = calcular_retencoes(_nota("10000.00"))
    assert r.irrf == Decimal("150.00")
    assert r.crf == Decimal("465.00")
    assert r.inss == Decimal("1100.00")
    assert r.total == Decimal("1715.00")


def test_crf_isento_para_pf():
    r = calcular_retencoes(_nota("10000.00", TipoTomador.CPF))
    assert r.crf == Decimal("0.00")
    assert r.irrf == Decimal("150.00")  # IRRF continua


def test_crf_para_pf_quando_configurado():
    params = ParametrosRetencao(crf_isento_para_pf=False)
    r = calcular_retencoes(_nota("10000.00", TipoTomador.CPF), params)
    assert r.crf == Decimal("465.00")


def test_regra_de_dispensa_abaixo_do_minimo():
    # 500,00 -> IRRF 7,50 (dispensado, < 10) ; CRF 23,25 ; INSS 55,00
    r = calcular_retencoes(_nota("500.00"))
    assert r.irrf == Decimal("0.00")   # dispensado
    assert r.crf == Decimal("23.25")
    assert r.inss == Decimal("55.00")


def test_teto_inss():
    params = ParametrosRetencao(teto_inss=Decimal("1000.00"))
    r = calcular_retencoes(_nota("10000.00"), params)
    # INSS calculado sobre o teto 1000 -> 110,00
    assert r.inss == Decimal("110.00")


def test_arredondamento():
    # 33,33 * 1,5% = 0,49995 -> arredonda para 0,50, mas < 10 => dispensado
    r = calcular_retencoes(_nota("33.33"))
    assert r.irrf == Decimal("0.00")
