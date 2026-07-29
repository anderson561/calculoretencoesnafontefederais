from datetime import date

from retencoes.models import Cabecalho
from retencoes.relatorios.formatacao import linhas_cabecalho


def test_cabecalho_completo():
    cab = Cabecalho(empresa="Norte Contábil", cnpj="11222333000181",
                    competencia="07/2026", data_emissao="29/07/2026")
    linhas = dict(linhas_cabecalho(cab))
    assert linhas["Empresa"] == "Norte Contábil"
    assert linhas["CNPJ"] == "11.222.333/0001-81"  # máscara aplicada
    assert linhas["Competência"] == "07/2026"
    assert linhas["Emissão"] == "29/07/2026"


def test_cabecalho_vazio_preenche_emissao_com_hoje():
    linhas = dict(linhas_cabecalho(None))
    # Sem empresa/cnpj/competência: só a emissão aparece.
    assert set(linhas) == {"Emissão"}
    assert linhas["Emissão"] == date.today().strftime("%d/%m/%Y")


def test_cabecalho_omite_campos_vazios():
    cab = Cabecalho(empresa="Só a Empresa")
    linhas = dict(linhas_cabecalho(cab))
    assert "Empresa" in linhas
    assert "CNPJ" not in linhas
    assert "Competência" not in linhas
