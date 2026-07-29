"""Leitor de XML de NFSe (RF01) — padrões ABRASF e Nacional.

XMLs de NFSe variam bastante entre municípios (namespaces e nomes de tags).
Para maximizar a compatibilidade, este leitor:

- ignora namespaces (compara sempre pelo *nome local* da tag);
- compara nomes de tag de forma case-insensitive;
- ancora cada nota em um elemento reconhecível e, dentro dele, procura o
  bloco do tomador, o valor do serviço, o número e o nome.

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

# Nomes de tag (locais) para cada dado de interesse.
_TAGS_VALOR = ("valorservicos", "valorservico", "vserv", "vservprest")
_TAGS_NUMERO = ("numero", "nnfse", "numeronfse")
_TAGS_DATA = ("dataemissao", "dhemi", "demi", "competencia", "dataemissaonfse")
_TAGS_CNPJ = ("cnpj",)
_TAGS_CPF = ("cpf",)
_TAGS_CPFCNPJ = ("cpfcnpj",)
_TAGS_NOME = ("razaosocial", "nomerazaosocial", "xnome", "nome")


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


def _achar_bloco_tomador(nota: etree._Element) -> etree._Element:
    """Retorna o subelemento do tomador (para não pegar o documento do prestador)."""
    for filho in nota.iter():
        nome = _local(filho.tag)
        if "tomador" in nome or "tomadorservico" in nome:
            return filho
    return nota  # fallback: procura na nota inteira


def _achar_bloco_prestador(nota: etree._Element) -> etree._Element | None:
    """Retorna o subelemento do prestador (razão social + CNPJ), se houver."""
    for filho in nota.iter():
        if "prestador" in _local(filho.tag):
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


def ler_xml(caminho: str | Path) -> list[Nota]:
    """Lê um XML de NFSe e devolve a lista de notas normalizadas."""
    caminho = Path(caminho)
    parser = etree.XMLParser(recover=True, resolve_entities=False, no_network=True)
    arvore = etree.parse(str(caminho), parser)
    raiz = arvore.getroot()

    notas: list[Nota] = []
    for i, no in enumerate(_achar_ancoras(raiz), start=1):
        bloco_tomador = _achar_bloco_tomador(no)
        documento = _extrair_documento(bloco_tomador)
        tipo, doc = classificar_tomador(documento)

        bloco_prestador = _achar_bloco_prestador(no)
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
                origem=caminho.name,
            )
        )
    return notas


def apenas_digitos_doc(doc: str | None) -> str | None:
    """Mantém só os dígitos de um documento (ou None)."""
    if not doc:
        return None
    d = "".join(c for c in doc if c.isdigit())
    return d or None
