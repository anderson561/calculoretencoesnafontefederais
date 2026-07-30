from datetime import date
from decimal import Decimal

from retencoes.calculo import calcular_retencoes
from retencoes.models import Nota, NotaCalculada, TipoTomador
from retencoes.relatorios.agregacao import agregar_trimestral

CNPJ = "11222333000181"


def _nc(numero, valor, data, irrf=None):
    nota = Nota(numero=numero, documento_tomador=CNPJ, tipo_tomador=TipoTomador.CNPJ,
                nome_tomador="Cliente", valor_bruto=Decimal(valor), data_emissao=data,
                irrf_informado=Decimal(irrf) if irrf is not None else None)
    return NotaCalculada(nota=nota, retencoes=calcular_retencoes(nota))


def test_soma_tres_meses_no_mesmo_trimestre():
    # Abr/Mai/Jun de 2026 -> mesmo trimestre (T2).
    notas = [
        _nc("1", "1000.00", date(2026, 4, 15), irrf="15.00"),
        _nc("2", "1000.00", date(2026, 5, 15), irrf="15.00"),
        _nc("3", "1000.00", date(2026, 6, 15), irrf="15.00"),
    ]
    linhas = agregar_trimestral(notas)
    assert len(linhas) == 1
    assert linhas[0].qtd_notas == 3
    assert linhas[0].valor_bruto == Decimal("3000.00")
    assert linhas[0].total_irrf == Decimal("45.00")
    assert "2026" in linhas[0].rotulo


def test_trimestres_diferentes_nao_somam():
    notas = [
        _nc("1", "1000.00", date(2026, 3, 31)),  # T1
        _nc("2", "1000.00", date(2026, 4, 1)),   # T2
    ]
    linhas = agregar_trimestral(notas)
    assert len(linhas) == 2
    assert [l.qtd_notas for l in linhas] == [1, 1]


def test_notas_sem_data_ficam_em_bucket_proprio_no_fim():
    notas = [
        _nc("1", "1000.00", date(2026, 4, 1)),
        _nc("2", "1000.00", None),
    ]
    linhas = agregar_trimestral(notas)
    assert len(linhas) == 2
    assert linhas[-1].rotulo == "Sem data"
    assert linhas[-1].qtd_notas == 1
