from decimal import Decimal

from retencoes.calculo import calcular_retencoes
from retencoes.models import Nota, NotaCalculada, TipoTomador
from retencoes.relatorios.agregacao import agregar_analitico


def _nc(numero, doc, tipo, valor):
    nota = Nota(numero=numero, documento_tomador=doc, tipo_tomador=tipo,
                nome_tomador=None, valor_bruto=Decimal(valor))
    return NotaCalculada(nota=nota, retencoes=calcular_retencoes(nota))


def test_total_geral_soma_os_tres_blocos():
    notas = [
        _nc("1", "11222333000181", TipoTomador.CNPJ, "10000.00"),
        _nc("2", "11222333000181", TipoTomador.CNPJ, "5000.00"),
        _nc("3", "11144477735", TipoTomador.CPF, "3000.00"),
        _nc("4", "", TipoTomador.SEM_DOCUMENTO, "2000.00"),
    ]
    total = agregar_analitico(notas).total_geral()

    assert total.qtd_notas == 4
    assert total.valor_bruto == Decimal("20000.00")
    # IRRF 1,5% sobre 20.000 = 300 (todas as notas acima do mínimo de R$10)
    assert total.total_irrf == Decimal("300.00")
