# Changelog

Este projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.3.0] — 2026-08-09

### Alterado
- **Mínimo de dispensa (R$ 10,00) deixou de ser configurável.** Removido o
  campo "Mínimo p/ retenção" da GUI e a opção `--minimo` do CLI — o valor é
  fixo (definido em lei), evitando alteração acidental por operador.
- **Campo "Salvar relatório em" agora nasce vazio e é obrigatório.** O botão
  "Gerar relatório" só é liberado depois que **Entrada** e **Saída**
  estiverem ambos preenchidos (seja via diálogo ou digitação manual),
  eliminando o antigo comportamento de gerar com um caminho padrão
  pré-preenchido sem o usuário escolher explicitamente.

## [1.2.0] — 2026-07-31

### Adicionado
- **Exclusão automática de nota substituída (`<NfseSubstituida>`).** Quando
  o município reemite uma NFSe apontando qual nota original ela substitui
  (ex.: Camaçari/BA) e ambas estiverem no mesmo lote processado, a nota
  original é excluída do total, evitando duplicidade de retenção. `processar()`
  passa a informar também a quantidade de notas excluídas por substituição;
  CLI e GUI avisam quando isso ocorre. Cobre apenas a tag estruturada
  ABRASF — não interpreta menções em texto livre (ex.: campo "Outras
  Informações").

## [1.1.0] — 2026-07-31

### Adicionado
- **Aviso de nova versão disponível.** A GUI consulta em segundo plano
  (sem travar a janela) a API de Releases do GitHub; se houver uma versão
  mais nova que a instalada, mostra um link clicável que abre a página de
  download no navegador. Não baixa nem instala nada sozinho. Se não houver
  internet ou o GitHub estiver indisponível, falha em silêncio — o
  aplicativo continua funcionando 100% offline.

## [1.0.1] — 2026-07-31

### Corrigido
- **Leiaute ABRASF "achatado" (ex.: Lauro de Freitas/BA) não era reconhecido
  como lote.** Municípios cujo `<CompNfse>` não tem o envelope
  `<Nfse><InfNfse>` faziam o parser tratar o **lote inteiro como uma única
  nota**, descartando silenciosamente as demais notas (e seus tomadores e
  retenções). Adicionada âncora `compnfse` como fallback de detecção de nota.

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
