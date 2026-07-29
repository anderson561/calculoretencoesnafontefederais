from retencoes.models import TipoTomador
from retencoes.sanitizacao import (
    apenas_digitos,
    classificar_tomador,
    cnpj_valido,
    cpf_valido,
)

# Documentos de teste conhecidos e válidos.
CNPJ_OK = "11.222.333/0001-81"
CPF_OK = "111.444.777-35"


def test_apenas_digitos_remove_pontuacao():
    assert apenas_digitos("11.222.333/0001-81") == "11222333000181"
    assert apenas_digitos(None) == ""


def test_cnpj_valido():
    assert cnpj_valido(CNPJ_OK)
    assert not cnpj_valido("11.222.333/0001-99")
    assert not cnpj_valido("00000000000000")


def test_cpf_valido():
    assert cpf_valido(CPF_OK)
    assert not cpf_valido("111.444.777-00")
    assert not cpf_valido("11111111111")


def test_classificar_cnpj():
    tipo, doc = classificar_tomador(CNPJ_OK)
    assert tipo == TipoTomador.CNPJ
    assert doc == "11222333000181"


def test_classificar_cpf():
    tipo, doc = classificar_tomador(CPF_OK)
    assert tipo == TipoTomador.CPF
    assert doc == "11144477735"


def test_classificar_sem_documento():
    assert classificar_tomador("") == (TipoTomador.SEM_DOCUMENTO, "")
    assert classificar_tomador(None) == (TipoTomador.SEM_DOCUMENTO, "")
    # Documento inválido cai em SEM_DOCUMENTO, mas preserva os dígitos.
    tipo, doc = classificar_tomador("123")
    assert tipo == TipoTomador.SEM_DOCUMENTO
    assert doc == "123"
