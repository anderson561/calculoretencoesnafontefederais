# Changelog

Este projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.0.0] — 2026-07-30

Primeira versão estável. Encerra a fase inicial de validação contra XMLs reais
de NFSe e estabiliza as regras de negócio e o formato de relatório.

### Regras de negócio
- Retenção federal (IRRF, CRF = PIS/COFINS/CSLL, INSS) é apurada **somente**
  para tomador **CNPJ**; CPF e tomador sem documento nunca retêm.
- O sistema **não aplica alíquota alguma** — soma apenas os valores de
  retenção **já informados** na origem (XML da NFSe ou colunas opcionais da
  planilha). Imposto não informado permanece em branco ("-"), nunca R$ 0,00.
- Acúmulo de IRRF por **mesma data de emissão** (não por competência/mês).
- Identificação do prestador é sempre extraída do XML da nota, nunca digitada.

### Ingestão de XML — três leiautes de NFSe suportados e validados
- **ABRASF clássico** (`Prestador`/`Tomador`).
- **NFSe Nacional** (`sped.fazenda.gov.br/nfse`, tags `emit`/`prest`/`toma`):
  IRRF em `vRetIRRF`, INSS em `vRetCP` (Contribuição Previdenciária).
- **ABRASF variante Salvador/BA**, com lotes de múltiplas notas de múltiplos
  prestadores em um único XML (`PrestadorServico`/`TomadorServico`,
  `ValorPis`/`ValorCofins`/`ValorCsll`/`ValorInss`/`ValorIr`).
- Parser por *matching* exato de nome de tag (não substring), evitando
  contaminação entre blocos de tomador/prestador.

### Relatório
- Saída **exclusivamente em PDF**, com três seções: Sintético (totais por
  tipo de tomador), Analítico (uma linha por nota agrupada por tomador, com
  subtotal) e Trimestral (soma a cada trimestre civil).
- Texto do cabeçalho e das células escapado corretamente (corrige
  truncamento silencioso de razão social/nome com caracteres `<`, `>`, `&`).
- Quebra de texto automática na coluna Nome/Razão Social.

### Infraestrutura
- Suíte de testes (pytest) cobrindo os três leiautes de XML, planilha,
  cálculo, agregação e geração de PDF.
- CI (GitHub Actions) rodando a suíte em Linux e Windows a cada push.
- Empacotamento em `.exe` (PyInstaller) e workflow de Release automático por
  tag `v*`.
