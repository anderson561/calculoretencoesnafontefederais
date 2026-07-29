from datetime import date

from retencoes.datas import competencia_de, parse_data


def test_parse_iso():
    assert parse_data("2026-07-15") == date(2026, 7, 15)


def test_parse_br():
    assert parse_data("15/07/2026") == date(2026, 7, 15)


def test_parse_datetime():
    assert parse_data("2026-07-15T10:20:30") == date(2026, 7, 15)
    assert parse_data("15/07/2026 10:20") == date(2026, 7, 15)


def test_parse_competencia_mes_ano():
    assert parse_data("07/2026") == date(2026, 7, 1)
    assert parse_data("2026-07") == date(2026, 7, 1)


def test_parse_invalido_e_vazio():
    assert parse_data("") is None
    assert parse_data(None) is None
    assert parse_data("texto") is None


def test_competencia_de():
    assert competencia_de(date(2026, 7, 15)) == "07/2026"
    assert competencia_de(None) is None
