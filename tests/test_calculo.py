from decimal import Decimal

from retencoes.calculo import calcular_retencoes
from retencoes.config import ParametrosRetencao
from retencoes.models import Nota, TipoTomador


def _nota(valor, tipo=TipoTomador.CNPJ, irrf=None, crf=None, inss=None):
    doc = "11222333000181" if tipo == TipoTomador.CNPJ else ("11144477735" if tipo == TipoTomador.CPF else "")
    return Nota(
        numero="1",
        documento_tomador=doc,
        tipo_tomador=tipo,
        nome_tomador="Teste",
        valor_bruto=Decimal(str(valor)),
        irrf_informado=Decimal(str(irrf)) if irrf is not None else None,
        crf_informado=Decimal(str(crf)) if crf is not None else None,
        inss_informado=Decimal(str(inss)) if inss is not None else None,
    )


def test_usa_valores_informados_sem_aplicar_aliquota():
    r = calcular_retencoes(_nota("10000.00", irrf="150.00", crf="465.00", inss="1100.00"))
    assert r.irrf == Decimal("150.00")
    assert r.crf == Decimal("465.00")
    assert r.inss == Decimal("1100.00")


def test_imposto_nao_informado_fica_none():
    # Nada foi informado -> nada é calculado (None, não zero).
    r = calcular_retencoes(_nota("10000.00"))
    assert r.irrf is None
    assert r.crf is None
    assert r.inss is None


def test_pessoa_fisica_nunca_retem_mesmo_se_informado():
    r = calcular_retencoes(_nota("10000.00", TipoTomador.CPF, irrf="150.00", crf="465.00", inss="1100.00"))
    assert r.irrf == Decimal("0.00")
    assert r.crf == Decimal("0.00")
    assert r.inss == Decimal("0.00")


def test_sem_documento_nunca_retem():
    r = calcular_retencoes(_nota("10000.00", TipoTomador.SEM_DOCUMENTO, irrf="150.00"))
    assert (r.irrf, r.crf, r.inss) == (Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))


def test_irrf_informado_devolvido_bruto_sem_dispensa_no_calculo():
    # A dispensa do IRRF é decidida no acúmulo por data, não aqui.
    r = calcular_retencoes(_nota("500.00", irrf="7.50"))
    assert r.irrf == Decimal("7.50")


def test_crf_informado_dispensado_abaixo_do_minimo():
    r = calcular_retencoes(_nota("100.00", crf="4.65", inss="11.00"))
    assert r.crf == Decimal("0.00")
    assert r.inss == Decimal("11.00")


def test_crf_informado_como_zero_permanece_zero_nao_none():
    # Informado explicitamente como 0.00 é diferente de não informado.
    r = calcular_retencoes(_nota("10000.00", crf="0.00"))
    assert r.crf == Decimal("0.00")


def test_minimo_configuravel():
    # Com mínimo abaixado para 3,00, um CRF informado de 4,65 (>= 3,00) é mantido.
    params = ParametrosRetencao(valor_minimo_retencao=Decimal("3.00"))
    r = calcular_retencoes(_nota("100.00", crf="4.65"), params)
    assert r.crf == Decimal("4.65")
