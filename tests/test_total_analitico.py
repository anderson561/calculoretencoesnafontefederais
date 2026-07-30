from decimal import Decimal

from retencoes.calculo import calcular_retencoes
from retencoes.models import Nota, NotaCalculada, TipoTomador
from retencoes.relatorios.agregacao import agregar_analitico


def _nc(numero, doc, tipo, valor, irrf=None, inss=None):
    nota = Nota(numero=numero, documento_tomador=doc, tipo_tomador=tipo,
                nome_tomador=None, valor_bruto=Decimal(valor),
                irrf_informado=Decimal(irrf) if irrf is not None else None,
                inss_informado=Decimal(inss) if inss is not None else None)
    return NotaCalculada(nota=nota, retencoes=calcular_retencoes(nota))


def test_total_geral_soma_os_tres_blocos():
    notas = [
        _nc("1", "11222333000181", TipoTomador.CNPJ, "10000.00", irrf="150.00", inss="1100.00"),
        _nc("2", "11222333000181", TipoTomador.CNPJ, "5000.00", irrf="75.00", inss="550.00"),
        _nc("3", "11144477735", TipoTomador.CPF, "3000.00"),
        _nc("4", "", TipoTomador.SEM_DOCUMENTO, "2000.00"),
    ]
    total = agregar_analitico(notas).total_geral()

    assert total.qtd_notas == 4
    assert total.valor_bruto == Decimal("20000.00")
    # Só as notas CNPJ retêm, e só o que foi informado: 150,00 + 75,00 = 225,00.
    # CPF e sem documento não retêm.
    assert total.total_irrf == Decimal("225.00")
    assert total.total_inss == Decimal("1650.00")


def test_notas_sem_imposto_informado_nao_quebram_o_total():
    # Nenhuma nota informou imposto -> total fica 0,00 (soma de "nada"), sem erro.
    notas = [_nc("1", "11222333000181", TipoTomador.CNPJ, "10000.00")]
    total = agregar_analitico(notas).total_geral()
    assert total.total_irrf == Decimal("0.00")
    assert total.total_inss == Decimal("0.00")
