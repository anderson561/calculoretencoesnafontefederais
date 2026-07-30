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
