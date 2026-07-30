from pathlib import Path
from datetime import date
from decimal import Decimal

from retencoes.ingestao import ler_xml
from retencoes.models import TipoTomador

# Amostra simplificada no estilo ABRASF (com namespace), com Prestador e Tomador.
XML_ABRASF = """<?xml version="1.0" encoding="UTF-8"?>
<ConsultarNfseResposta xmlns="http://www.abrasf.org.br/nfse.xsd">
  <ListaNfse>
    <CompNfse>
      <Nfse>
        <InfNfse>
          <Numero>2024001</Numero>
          <DataEmissao>2026-07-15</DataEmissao>
          <ValoresNfse><ValorServicos>10000.00</ValorServicos></ValoresNfse>
          <DeclaracaoPrestacaoServico>
            <Servico><Valores><ValorServicos>10000.00</ValorServicos></Valores></Servico>
            <Prestador>
              <IdentificacaoPrestador>
                <CpfCnpj><Cnpj>45723174000110</Cnpj></CpfCnpj>
              </IdentificacaoPrestador>
              <RazaoSocial>Norte Contábil Ltda</RazaoSocial>
            </Prestador>
            <Tomador>
              <IdentificacaoTomador>
                <CpfCnpj><Cnpj>11222333000181</Cnpj></CpfCnpj>
              </IdentificacaoTomador>
              <RazaoSocial>Empresa Alpha Ltda</RazaoSocial>
            </Tomador>
          </DeclaracaoPrestacaoServico>
        </InfNfse>
      </Nfse>
    </CompNfse>
  </ListaNfse>
</ConsultarNfseResposta>
"""


def test_ler_xml_abrasf(tmp_path: Path):
    arq = tmp_path / "nota.xml"
    arq.write_text(XML_ABRASF, encoding="utf-8")

    notas = ler_xml(arq)
    assert len(notas) == 1
    nota = notas[0]
    # Tomador
    assert nota.tipo_tomador == TipoTomador.CNPJ
    assert nota.documento_tomador == "11222333000181"
    assert nota.nome_tomador == "Empresa Alpha Ltda"
    assert str(nota.valor_bruto) == "10000.00"
    assert nota.numero == "2024001"
    assert nota.data_emissao == date(2026, 7, 15)
    # Prestador extraído do XML
    assert nota.prestador_nome == "Norte Contábil Ltda"
    assert nota.prestador_cnpj == "45723174000110"


# Amostra sintética (dados fictícios) no leiaute NFS-e Nacional
# (sped.fazenda.gov.br/nfse), que usa <emit>/<prest>/<toma> em vez de
# Prestador/Tomador do ABRASF. Estrutura equivalente a uma nota real, mas com
# CNPJs, nomes e valores inventados — sem nada sensível.
XML_NACIONAL = """<?xml version="1.0" encoding="UTF-8"?>
<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse" versao="1.01">
  <infNFSe Id="NFS0000000000000000000000000000000000000123">
    <nNFSe>555</nNFSe>
    <emit>
      <CNPJ>45723174000110</CNPJ>
      <xNome>Prestador Exemplo Ltda</xNome>
    </emit>
    <DPS xmlns="http://www.sped.fazenda.gov.br/nfse" versao="1.01">
      <infDPS Id="DPS00000000000000000000000000000000000000">
        <dhEmi>2026-05-04T11:22:50-03:00</dhEmi>
        <prest>
          <CNPJ>45723174000110</CNPJ>
        </prest>
        <toma>
          <CNPJ>11222333000181</CNPJ>
          <xNome>Tomador Exemplo S.A.</xNome>
        </toma>
        <valores>
          <vServPrest><vServ>100000.00</vServ></vServPrest>
          <trib>
            <tribFed><vRetIRRF>1500.00</vRetIRRF></tribFed>
          </trib>
        </valores>
      </infDPS>
    </DPS>
  </infNFSe>
</NFSe>
"""


def test_ler_xml_nacional_nao_troca_tomador_pelo_prestador(tmp_path: Path):
    arq = tmp_path / "nota_nacional.xml"
    arq.write_text(XML_NACIONAL, encoding="utf-8")

    notas = ler_xml(arq)
    assert len(notas) == 1
    nota = notas[0]

    # Tomador correto (não pode ser o CNPJ/nome do emitente/prestador).
    assert nota.tipo_tomador == TipoTomador.CNPJ
    assert nota.documento_tomador == "11222333000181"
    assert nota.nome_tomador == "Tomador Exemplo S.A."

    # Prestador correto, extraído de <emit>.
    assert nota.prestador_cnpj == "45723174000110"
    assert nota.prestador_nome == "Prestador Exemplo Ltda"

    assert nota.numero == "555"
    assert str(nota.valor_bruto) == "100000.00"
    assert nota.data_emissao == date(2026, 5, 4)

    # IRRF informado no XML é extraído; CRF/INSS não informados ficam None.
    assert nota.irrf_informado == Decimal("1500.00")
    assert nota.crf_informado is None
    assert nota.inss_informado is None


# Amostra sintética (dados fictícios) no leiaute ABRASF usado por Salvador/BA,
# baixado em lote: várias notas do MESMO prestador dentro de um único XML,
# usando <PrestadorServico>/<TomadorServico> e Valor{Pis,Cofins,Csll,Inss,Ir}
# dentro de <Servico><Valores> (em vez de vRetIRRF do leiaute Nacional).
XML_ABRASF_LOTE = """<?xml version='1.0' encoding='ISO-8859-1'?>
<ConsultarNfseResposta xmlns='http://www.abrasf.org.br/ABRASF/arquivos/nfse.xsd'>
<ListaNfse>
<CompNfse><Nfse><InfNfse>
<Numero>7319</Numero>
<DataEmissao>2026-04-29T10:35:46-03:00</DataEmissao>
<Servico><Valores>
<ValorServicos>800</ValorServicos>
<ValorPis>5,20</ValorPis>
<ValorCofins>24</ValorCofins>
<ValorInss>0</ValorInss>
<ValorIr>12</ValorIr>
<ValorCsll>8</ValorCsll>
</Valores></Servico>
<PrestadorServico>
<IdentificacaoPrestador><Cnpj>45.723.174/0001-10</Cnpj></IdentificacaoPrestador>
<RazaoSocial>Prestador Exemplo Ltda</RazaoSocial>
</PrestadorServico>
<TomadorServico>
<IdentificacaoTomador><CpfCnpj><Cnpj>11.222.333/0001-81</Cnpj></CpfCnpj></IdentificacaoTomador>
<RazaoSocial>Tomador Exemplo Um Ltda</RazaoSocial>
</TomadorServico>
</InfNfse></Nfse></CompNfse>
<CompNfse><Nfse><InfNfse>
<Numero>7106</Numero>
<DataEmissao>2026-04-02T11:24:34-03:00</DataEmissao>
<Servico><Valores>
<ValorServicos>2431,50</ValorServicos>
<ValorPis>15,80</ValorPis>
<ValorCofins>72,94</ValorCofins>
<ValorInss>0</ValorInss>
<ValorIr>36,47</ValorIr>
<ValorCsll>24,32</ValorCsll>
</Valores></Servico>
<PrestadorServico>
<IdentificacaoPrestador><Cnpj>45.723.174/0001-10</Cnpj></IdentificacaoPrestador>
<RazaoSocial>Prestador Exemplo Ltda</RazaoSocial>
</PrestadorServico>
<TomadorServico>
<IdentificacaoTomador><CpfCnpj><Cnpj>02.931.604/0001-87</Cnpj></CpfCnpj></IdentificacaoTomador>
<RazaoSocial>Tomador Exemplo Dois S.A.</RazaoSocial>
</TomadorServico>
</InfNfse></Nfse></CompNfse>
</ListaNfse>
</ConsultarNfseResposta>
"""


def test_ler_xml_abrasf_lote_com_varias_notas_do_mesmo_prestador(tmp_path: Path):
    arq = tmp_path / "lote.xml"
    arq.write_text(XML_ABRASF_LOTE, encoding="utf-8")

    notas = ler_xml(arq)
    assert len(notas) == 2

    nota1, nota2 = notas
    # Mesmo prestador nas duas notas.
    assert nota1.prestador_nome == nota2.prestador_nome == "Prestador Exemplo Ltda"
    assert nota1.prestador_cnpj == nota2.prestador_cnpj == "45723174000110"

    # Tomadores diferentes, sem contaminação entre as notas.
    assert nota1.numero == "7319"
    assert nota1.documento_tomador == "11222333000181"
    assert nota1.valor_bruto == Decimal("800")
    assert nota1.irrf_informado == Decimal("12")
    assert nota1.crf_informado == Decimal("37.20")  # 5,20 + 24 + 8
    assert nota1.inss_informado == Decimal("0")

    assert nota2.numero == "7106"
    assert nota2.documento_tomador == "02931604000187"
    assert nota2.valor_bruto == Decimal("2431.50")
    assert nota2.irrf_informado == Decimal("36.47")
    assert nota2.crf_informado == Decimal("113.06")  # 15,80 + 72,94 + 24,32
    assert nota2.inss_informado == Decimal("0")
