"""Leitor de XML de NFSe (RF01) — padrões ABRASF e Nacional.

XMLs de NFSe variam bastante entre municípios/leiautes (namespaces e nomes de
tags). Para maximizar a compatibilidade, este leitor:

- ignora namespaces (compara sempre pelo *nome local* da tag);
- compara nomes de tag de forma case-insensitive;
- ancora cada nota em um elemento reconhecível e, dentro dele, procura o
  bloco do tomador e do prestador por um conjunto de nomes de tag *exatos*
  (não por substring — "toma" não deve casar por acidente com outra tag).

Não cobre 100% dos layouts proprietários — para esses, use a planilha padrão.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from lxml import etree

from ..datas import parse_data
from ..models import Nota
from ..sanitizacao import classificar_tomador

# Elementos que representam "uma nota". Preferimos o mais interno disponível.
_ANCORAS_NOTA = ("infnfse", "infdeclaracaoprestacaoservico", "nfse")

# Nomes de tag (locais, exatos) do bloco do tomador/prestador.
# ABRASF usa "Tomador"/"TomadorServico" e "Prestador"/"PrestadorServico"; o
# leiaute Nacional (sped.fazenda.gov.br/nfse) usa "toma", "emit" e "prest".
_TAGS_BLOCO_TOMADOR = {"tomador", "tomadorservico", "toma"}
_TAGS_BLOCO_PRESTADOR = {"prestador", "prestadorservico", "emit", "prest"}

# Nomes de tag (locais) para cada dado de interesse.
_TAGS_VALOR = ("valorservicos", "valorservico", "vserv", "vservprest")
_TAGS_NUMERO = ("numero", "nnfse", "numeronfse")
_TAGS_DATA = ("dataemissao", "dhemi", "demi", "competencia", "dataemissaonfse")
_TAGS_CNPJ = ("cnpj",)
_TAGS_CPF = ("cpf",)
_TAGS_CPFCNPJ = ("cpfcnpj",)
_TAGS_NOME = ("razaosocial", "nomerazaosocial", "xnome", "nome")

# Valores de retenção federal já informados no XML. Cobre dois leiautes
# validados contra XML real: o Nacional (sped.fazenda.gov.br/nfse, tag
# vRetIRRF) e uma variante ABRASF que traz Valor{Pis,Cofins,Csll,Inss,Ir}
# dentro de <Servico><Valores>.
_TAGS_IRRF_INFORMADO = ("vretirrf", "valorir")
_TAGS_PIS_INFORMADO = ("vretpis", "valorpis")
_TAGS_COFINS_INFORMADO = ("vretcofins", "valorcofins")
_TAGS_CSLL_INFORMADO = ("vretcsll", "valorcsll")
_TAGS_INSS_INFORMADO = ("vretinss", "valorinss")


def _local(tag: object) -> str:
    """Nome local da tag, sem namespace e em minúsculas."""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1].lower()


def _achar_ancoras(raiz: etree._Element) -> list[etree._Element]:
    """Encontra os elementos que representam cada nota."""
    for nome in _ANCORAS_NOTA:
        nos = [e for e in raiz.iter() if _local(e.tag) == nome]
        if nos:
            return nos
    return [raiz]  # documento inteiro tratado como uma nota


def _primeiro_texto(elemento: etree._Element, nomes: tuple[str, ...]) -> str | None:
    """Texto do primeiro descendente cujo nome local esteja em ``nomes``."""
    alvos = set(nomes)
    for filho in elemento.iter():
        if _local(filho.tag) in alvos and filho.text and filho.text.strip():
            return filho.text.strip()
    return None


def _achar_bloco(nota: etree._Element, nomes: set[str]) -> etree._Element | None:
    """Retorna o primeiro subelemento cujo nome local esteja em ``nomes``."""
    for filho in nota.iter():
        if _local(filho.tag) in nomes:
            return filho
    return None


def _extrair_documento(bloco: etree._Element) -> str | None:
    """Extrai CNPJ/CPF do bloco do tomador, cobrindo variações de tag."""
    cnpj = _primeiro_texto(bloco, _TAGS_CNPJ)
    if cnpj:
        return cnpj
    cpf = _primeiro_texto(bloco, _TAGS_CPF)
    if cpf:
        return cpf
    return _primeiro_texto(bloco, _TAGS_CPFCNPJ)


def _para_decimal(texto: str | None) -> Decimal:
    if not texto:
        return Decimal("0")
    texto = texto.strip().replace(" ", "")
    if "," in texto:  # formato BR
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError(f"Valor de serviço inválido no XML: {texto!r}") from exc


def _para_decimal_opt(texto: str | None) -> Decimal | None:
    """Como :func:`_para_decimal`, mas devolve ``None`` se a tag não existir."""
    if texto is None:
        return None
    return _para_decimal(texto)


def ler_xml(caminho: str | Path) -> list[Nota]:
    """Lê um XML de NFSe e devolve a lista de notas normalizadas."""
    caminho = Path(caminho)
    parser = etree.XMLParser(recover=True, resolve_entities=False, no_network=True)
    arvore = etree.parse(str(caminho), parser)
    raiz = arvore.getroot()

    notas: list[Nota] = []
    for i, no in enumerate(_achar_ancoras(raiz), start=1):
        bloco_tomador = _achar_bloco(no, _TAGS_BLOCO_TOMADOR)
        if bloco_tomador is None:
            bloco_tomador = no
        documento = _extrair_documento(bloco_tomador)
        tipo, doc = classificar_tomador(documento)

        bloco_prestador = _achar_bloco(no, _TAGS_BLOCO_PRESTADOR)
        prestador_nome = _primeiro_texto(bloco_prestador, _TAGS_NOME) if bloco_prestador is not None else None
        prestador_doc = _extrair_documento(bloco_prestador) if bloco_prestador is not None else None

        notas.append(
            Nota(
                numero=_primeiro_texto(no, _TAGS_NUMERO) or str(i),
                documento_tomador=doc,
                tipo_tomador=tipo,
                nome_tomador=_primeiro_texto(bloco_tomador, _TAGS_NOME),
                valor_bruto=_para_decimal(_primeiro_texto(no, _TAGS_VALOR)),
                data_emissao=parse_data(_primeiro_texto(no, _TAGS_DATA)),
                prestador_nome=prestador_nome,
                prestador_cnpj=(apenas_digitos_doc(prestador_doc)),
                irrf_informado=_para_decimal_opt(_primeiro_texto(no, _TAGS_IRRF_INFORMADO)),
                crf_informado=_crf_informado(no),
                inss_informado=_para_decimal_opt(_primeiro_texto(no, _TAGS_INSS_INFORMADO)),
                origem=caminho.name,
            )
        )
    return notas


def _crf_informado(no: etree._Element) -> Decimal | None:
    """Soma PIS + COFINS + CSLL informados; ``None`` se nenhum foi informado."""
    partes = (
        _primeiro_texto(no, _TAGS_PIS_INFORMADO),
        _primeiro_texto(no, _TAGS_COFINS_INFORMADO),
        _primeiro_texto(no, _TAGS_CSLL_INFORMADO),
    )
    if all(p is None for p in partes):
        return None
    return sum((_para_decimal(p) for p in partes if p is not None), Decimal("0"))


def apenas_digitos_doc(doc: str | None) -> str | None:
    """Mantém só os dígitos de um documento (ou None)."""
    if not doc:
        return None
    d = "".join(c for c in doc if c.isdigit())
    return d or None
