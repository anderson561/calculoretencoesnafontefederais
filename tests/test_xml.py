from pathlib import Path

from retencoes.ingestao import ler_xml
from retencoes.models import TipoTomador

# Amostra simplificada no estilo ABRASF (com namespace).
XML_ABRASF = """<?xml version="1.0" encoding="UTF-8"?>
<ConsultarNfseResposta xmlns="http://www.abrasf.org.br/nfse.xsd">
  <ListaNfse>
    <CompNfse>
      <Nfse>
        <InfNfse>
          <Numero>2024001</Numero>
          <ValoresNfse><ValorServicos>10000.00</ValorServicos></ValoresNfse>
          <DeclaracaoPrestacaoServico>
            <Servico><Valores><ValorServicos>10000.00</ValorServicos></Valores></Servico>
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
    assert nota.tipo_tomador == TipoTomador.CNPJ
    assert nota.documento_tomador == "11222333000181"
    assert nota.nome_tomador == "Empresa Alpha Ltda"
    assert str(nota.valor_bruto) == "10000.00"
    assert nota.numero == "2024001"
