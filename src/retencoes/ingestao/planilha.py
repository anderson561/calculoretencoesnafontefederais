"""Leitor da planilha padrão CSV/XLSX (RF01 - fallback universal).

Colunas esperadas (nomes flexíveis, sem depender de maiúsculas/acentos):

- numero            -> "numero", "numero_nota", "nota"
- documento_tomador -> "documento", "cnpj_cpf", "documento_tomador", "cpf_cnpj"
- nome_tomador      -> "nome", "razao_social", "nome_tomador"        (opcional)
- valor_bruto       -> "valor", "valor_bruto", "valor_servico"
"""
from __future__ import annotations

import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from ..datas import parse_data
from ..models import Nota
from ..sanitizacao import classificar_tomador

# Mapeia possíveis nomes de coluna -> campo canônico.
_ALIASES = {
    "numero": {"numero", "numeronota", "numero_nota", "nota", "num", "nnfse"},
    "documento": {
        "documento", "documentotomador", "documento_tomador",
        "cnpjcpf", "cnpj_cpf", "cpfcnpj", "cpf_cnpj", "cnpj", "cpf",
    },
    "nome": {"nome", "nometomador", "nome_tomador", "razaosocial", "razao_social"},
    "valor": {
        "valor", "valorbruto", "valor_bruto", "valorservico",
        "valor_servico", "valornota", "valor_nota",
    },
    "data": {
        "data", "dataemissao", "data_emissao", "emissao", "dtemissao",
        "competencia", "datanf", "datanota",
    },
}


def _normalizar(texto: str) -> str:
    """minúsculas, sem acentos, só alfanumérico e underscore."""
    txt = unicodedata.normalize("NFKD", str(texto))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = txt.strip().lower()
    return "".join(c if c.isalnum() else "_" for c in txt).strip("_")


def _mapear_colunas(colunas: list[str]) -> dict[str, str]:
    """Retorna {campo_canonico: nome_original_da_coluna}."""
    encontrado: dict[str, str] = {}
    for original in colunas:
        chave = _normalizar(original).replace("_", "")
        for campo, aliases in _ALIASES.items():
            if campo in encontrado:
                continue
            if chave in {a.replace("_", "") for a in aliases}:
                encontrado[campo] = original
    return encontrado


def _para_decimal(valor) -> Decimal:
    """Converte valores em formatos BR ('1.234,56') ou US ('1234.56')."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return Decimal("0")
    if isinstance(valor, (int,)):
        return Decimal(valor)
    if isinstance(valor, float):
        return Decimal(str(valor))
    texto = str(valor).strip()
    if not texto:
        return Decimal("0")
    texto = texto.replace("R$", "").replace(" ", "")
    # Formato brasileiro: milhar com "." e decimal com ","
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError(f"Valor bruto inválido: {valor!r}") from exc


def ler_planilha(caminho: str | Path) -> list[Nota]:
    """Lê uma planilha CSV/XLSX e devolve a lista de notas normalizadas."""
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".csv":
        df = pd.read_csv(caminho, dtype=str, sep=None, engine="python")
    else:
        df = pd.read_excel(caminho, dtype=str)

    mapa = _mapear_colunas(list(df.columns))
    faltando = {"documento", "valor"} - set(mapa)
    if faltando:
        raise ValueError(
            "Planilha sem colunas obrigatórias: "
            f"{', '.join(sorted(faltando))}. Colunas encontradas: "
            f"{list(df.columns)}"
        )

    notas: list[Nota] = []
    for i, linha in df.iterrows():
        documento = linha.get(mapa["documento"], "")
        tipo, doc = classificar_tomador(documento)
        nome = linha.get(mapa["nome"]) if "nome" in mapa else None
        if isinstance(nome, float) and pd.isna(nome):
            nome = None
        numero = linha.get(mapa["numero"]) if "numero" in mapa else None
        data = parse_data(linha.get(mapa["data"])) if "data" in mapa else None
        notas.append(
            Nota(
                numero=str(numero) if numero not in (None, "") else str(i + 1),
                documento_tomador=doc,
                tipo_tomador=tipo,
                nome_tomador=(str(nome).strip() if nome else None),
                valor_bruto=_para_decimal(linha.get(mapa["valor"])),
                data_emissao=data,
                origem=caminho.name,
            )
        )
    return notas
