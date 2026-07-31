from decimal import Decimal
from pathlib import Path

from retencoes.models import Nota, TipoTomador
from retencoes.pipeline import processar, remover_notas_substituidas

CSV = """numero;documento;nome;valor
1001;11.222.333/0001-81;Empresa Alpha Ltda;10000,00
1002;11.222.333/0001-81;Empresa Alpha Ltda;5000,00
1003;111.444.777-35;Joao Silva;3000,00
1004;;Consumidor Final;800,00
"""


def _csv(tmp_path: Path) -> Path:
    entrada = tmp_path / "notas.csv"
    entrada.write_text(CSV, encoding="utf-8")
    return entrada


def test_fluxo_pdf(tmp_path: Path):
    saida = tmp_path / "retencoes.pdf"
    gerados, qtd, qtd_substituidas = processar(_csv(tmp_path), saida)

    assert qtd == 4
    assert qtd_substituidas == 0
    assert len(gerados) == 1
    pdf = gerados[0]
    assert pdf.exists() and pdf.suffix == ".pdf"
    # Assinatura de um arquivo PDF válido.
    assert pdf.read_bytes()[:5] == b"%PDF-"


def test_saida_sempre_vira_pdf_mesmo_com_outra_extensao(tmp_path: Path):
    # O relatório só é gerado em PDF; qualquer extensão pedida é normalizada.
    saida = tmp_path / "retencoes.xlsx"
    gerados, _, _ = processar(_csv(tmp_path), saida)

    assert len(gerados) == 1
    assert gerados[0].suffix == ".pdf"
    assert gerados[0].exists()


def test_diretorio_com_multiplos_arquivos(tmp_path: Path):
    (tmp_path / "a.csv").write_text(CSV, encoding="utf-8")
    (tmp_path / "b.csv").write_text(CSV, encoding="utf-8")
    saida = tmp_path / "retencoes.pdf"

    _, qtd, _ = processar(tmp_path, saida)
    assert qtd == 8


CSV_SEM_IMPOSTO_INFORMADO = """numero;documento;nome;valor
1001;11.222.333/0001-81;Empresa Alpha Ltda;10000,00
"""

CSV_COM_IMPOSTO_INFORMADO = """numero;documento;nome;valor;irrf;crf;inss
1001;11.222.333/0001-81;Empresa Alpha Ltda;10000,00;150,00;465,00;1100,00
"""


def test_planilha_sem_colunas_de_imposto_nao_calcula_nada(tmp_path: Path):
    entrada = tmp_path / "notas.csv"
    entrada.write_text(CSV_SEM_IMPOSTO_INFORMADO, encoding="utf-8")
    saida = tmp_path / "retencoes.pdf"

    gerados, qtd, _ = processar(entrada, saida)
    assert qtd == 1
    assert gerados[0].exists()  # não deve lançar erro ao formatar valores None


def test_planilha_com_colunas_de_imposto_usa_valor_informado(tmp_path: Path):
    entrada = tmp_path / "notas.csv"
    entrada.write_text(CSV_COM_IMPOSTO_INFORMADO, encoding="utf-8")

    from retencoes.ingestao import ler_entrada
    from retencoes.pipeline import calcular_notas

    notas = ler_entrada(entrada)
    calculadas = calcular_notas(notas)
    assert calculadas[0].retencoes.irrf == Decimal("150.00")
    assert calculadas[0].retencoes.crf == Decimal("465.00")
    assert calculadas[0].retencoes.inss == Decimal("1100.00")


def _nota_simples(numero: str, prestador_cnpj: str, numero_substituida: str | None = None) -> Nota:
    return Nota(
        numero=numero,
        documento_tomador="11222333000181",
        tipo_tomador=TipoTomador.CNPJ,
        nome_tomador="Tomador Exemplo",
        valor_bruto=Decimal("1000.00"),
        prestador_cnpj=prestador_cnpj,
        irrf_informado=Decimal("100.00"),
        numero_substituida=numero_substituida,
    )


def test_remove_nota_substituida_do_mesmo_prestador():
    original = _nota_simples("597", "45723174000110")
    substituta = _nota_simples("598", "45723174000110", numero_substituida="597")

    mantidas, excluidas = remover_notas_substituidas([original, substituta])

    assert mantidas == [substituta]
    assert excluidas == [original]


def test_nao_remove_nota_de_prestador_diferente_com_mesmo_numero():
    # Número igual, mas prestadores diferentes: não deve haver contaminação.
    nota_prestador_a = _nota_simples("597", "45723174000110")
    nota_prestador_b = _nota_simples("597", "11222333000181")
    substituta = _nota_simples("598", "45723174000110", numero_substituida="597")

    mantidas, excluidas = remover_notas_substituidas(
        [nota_prestador_a, nota_prestador_b, substituta]
    )

    assert nota_prestador_a not in mantidas
    assert nota_prestador_b in mantidas
    assert substituta in mantidas
    assert excluidas == [nota_prestador_a]


def test_processar_exclui_nota_substituida_do_total(tmp_path: Path):
    xml = """<?xml version='1.0' encoding='UTF-8'?>
<GerarNfseResposta xmlns="http://www.abrasf.org.br/nfse.xsd"><ListaNfse>
<CompNfse><Nfse><InfNfse>
<Numero>597</Numero>
<DataEmissao>2026-07-15</DataEmissao>
<PrestadorServico><IdentificacaoPrestador><CpfCnpj><Cnpj>45723174000110</Cnpj></CpfCnpj></IdentificacaoPrestador><RazaoSocial>Prestador Exemplo Ltda</RazaoSocial></PrestadorServico>
<DeclaracaoPrestacaoServico><InfDeclaracaoPrestacaoServico>
<Servico><Valores><ValorServicos>9875.00</ValorServicos><ValorIr>148.13</ValorIr></Valores></Servico>
<Tomador><IdentificacaoTomador><CpfCnpj><Cnpj>11222333000181</Cnpj></CpfCnpj></IdentificacaoTomador><RazaoSocial>Tomador Exemplo Ltda</RazaoSocial></Tomador>
</InfDeclaracaoPrestacaoServico></DeclaracaoPrestacaoServico>
</InfNfse></Nfse></CompNfse>
<CompNfse><Nfse><InfNfse>
<Numero>598</Numero>
<DataEmissao>2026-07-16</DataEmissao>
<NfseSubstituida>597</NfseSubstituida>
<PrestadorServico><IdentificacaoPrestador><CpfCnpj><Cnpj>45723174000110</Cnpj></CpfCnpj></IdentificacaoPrestador><RazaoSocial>Prestador Exemplo Ltda</RazaoSocial></PrestadorServico>
<DeclaracaoPrestacaoServico><InfDeclaracaoPrestacaoServico>
<Servico><Valores><ValorServicos>9875.00</ValorServicos><ValorIr>148.13</ValorIr></Valores></Servico>
<Tomador><IdentificacaoTomador><CpfCnpj><Cnpj>11222333000181</Cnpj></CpfCnpj></IdentificacaoTomador><RazaoSocial>Tomador Exemplo Ltda</RazaoSocial></Tomador>
</InfDeclaracaoPrestacaoServico></DeclaracaoPrestacaoServico>
</InfNfse></Nfse></CompNfse>
</ListaNfse></GerarNfseResposta>
"""
    entrada = tmp_path / "lote.xml"
    entrada.write_text(xml, encoding="utf-8")
    saida = tmp_path / "retencoes.pdf"

    gerados, qtd, qtd_substituidas = processar(entrada, saida)

    assert qtd == 1  # só a nota 598 (598 substitui 597, que sai do total)
    assert qtd_substituidas == 1
    assert gerados[0].exists()
