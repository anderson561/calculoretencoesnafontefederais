"""Sanitização e classificação de documentos do tomador (RF02).

Remove pontuação, valida dígitos verificadores e classifica o documento
em CNPJ, CPF ou SEM_DOCUMENTO.
"""
from __future__ import annotations

import re

from .models import TipoTomador

_NAO_DIGITO = re.compile(r"\D")


def apenas_digitos(documento: str | None) -> str:
    """Remove tudo que não for dígito (pontos, traços, barras, espaços)."""
    if documento is None:
        return ""
    return _NAO_DIGITO.sub("", str(documento))


def _digito_por_pesos(digitos: str, pesos: list[int]) -> int:
    soma = sum(int(d) * p for d, p in zip(digitos, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(documento: str) -> bool:
    """Valida um CPF (11 dígitos) pelos dígitos verificadores."""
    cpf = apenas_digitos(documento)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    dv1 = _digito_por_pesos(cpf[:9], list(range(10, 1, -1)))
    dv2 = _digito_por_pesos(cpf[:10], list(range(11, 1, -1)))
    return cpf[9:] == f"{dv1}{dv2}"


def cnpj_valido(documento: str) -> bool:
    """Valida um CNPJ (14 dígitos) pelos dígitos verificadores."""
    cnpj = apenas_digitos(documento)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    dv1 = _digito_por_pesos(cnpj[:12], pesos1)
    dv2 = _digito_por_pesos(cnpj[:13], pesos2)
    return cnpj[12:] == f"{dv1}{dv2}"


def classificar_tomador(documento: str | None) -> tuple[TipoTomador, str]:
    """Classifica o documento do tomador.

    Retorna a tupla ``(tipo, documento_sanitizado)``.

    - 14 dígitos válidos  -> CNPJ
    - 11 dígitos válidos  -> CPF
    - vazio / inválido    -> SEM_DOCUMENTO (documento sanitizado devolvido tal
      como veio, para rastreabilidade)
    """
    doc = apenas_digitos(documento)
    if not doc:
        return TipoTomador.SEM_DOCUMENTO, ""
    if len(doc) == 14 and cnpj_valido(doc):
        return TipoTomador.CNPJ, doc
    if len(doc) == 11 and cpf_valido(doc):
        return TipoTomador.CPF, doc
    # Comprimento inesperado ou dígito verificador inválido.
    return TipoTomador.SEM_DOCUMENTO, doc
