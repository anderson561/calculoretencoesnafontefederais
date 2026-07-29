from decimal import Decimal

from retencoes.calculo import calcular_retencoes
from retencoes.config import ParametrosRetencao
from retencoes.models import Nota, TipoTomador


def _nota(valor, tipo=TipoTomador.CNPJ):
    doc = "11222333000181" if tipo == TipoTomador.CNPJ else ("11144477735" if tipo == TipoTomador.CPF else "")
    return Nota(
        numero="1",
        documento_tomador=doc,
        tipo_tomador=tipo,
        nome_tomador="Teste",
        valor_bruto=Decimal(str(valor)),
    )


def test_calculo_cnpj_valores_default():
    # CNPJ 10.000,00 -> IRRF 1,5% = 150 (bruto) ; CRF 4,65% = 465 ; INSS 11% = 1100
    r = calcular_retencoes(_nota("10000.00"))
    assert r.irrf == Decimal("150.00")
    assert r.crf == Decimal("465.00")
    assert r.inss == Decimal("1100.00")


def test_pessoa_fisica_nunca_retem():
    r = calcular_retencoes(_nota("10000.00", TipoTomador.CPF))
    assert r.irrf == Decimal("0.00")
    assert r.crf == Decimal("0.00")
    assert r.inss == Decimal("0.00")


def test_sem_documento_nunca_retem():
    r = calcular_retencoes(_nota("10000.00", TipoTomador.SEM_DOCUMENTO))
    assert (r.irrf, r.crf, r.inss) == (Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))


def test_irrf_devolvido_bruto_sem_dispensa_no_calculo():
    # A dispensa do IRRF é decidida no acúmulo por data, não aqui.
    r = calcular_retencoes(_nota("500.00"))
    assert r.irrf == Decimal("7.50")


def test_crf_dispensado_abaixo_do_minimo():
    # CNPJ 100,00 -> CRF 4,65 (< 10) dispensado; INSS 11,00 mantido.
    r = calcular_retencoes(_nota("100.00"))
    assert r.crf == Decimal("0.00")
    assert r.inss == Decimal("11.00")


def test_teto_inss():
    params = ParametrosRetencao(teto_inss=Decimal("1000.00"))
    r = calcular_retencoes(_nota("10000.00"), params)
    assert r.inss == Decimal("110.00")  # 11% sobre o teto 1000
