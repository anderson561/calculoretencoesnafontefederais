# Calculadora e Totalizadora de Retenções Federais (NFSe)

[![CI](https://github.com/anderson561/calculoretencoesnafontefederais/actions/workflows/ci.yml/badge.svg)](https://github.com/anderson561/calculoretencoesnafontefederais/actions/workflows/ci.yml)

Aplicação **Windows / Python** que processa lotes de Notas Fiscais de Serviço
Eletrônica (NFSe) e **totaliza** as retenções federais na fonte (**IRRF**,
**CRF** = PIS/COFINS/CSLL e **INSS**) já informadas na origem, gerando três
relatórios em Excel:

1. **Sintético** — totais por tipo de tomador (CNPJ / CPF / Sem documento).
2. **Analítico** — uma linha por nota, agrupada por tomador (CNPJ, CPF e sem documento), com subtotal.
3. **Trimestral** — totais por trimestre civil (soma a cada 3 meses).

Os relatórios podem ser exportados em **Excel (.xlsx)**, **PDF** ou **ambos**.

A aplicação roda **100% local e offline** (adequado a dados fiscais sensíveis /
LGPD), com **interface gráfica** e também linha de comando.

> ⚠️ **Aviso fiscal:** o software **não aplica alíquota alguma** — ele só
> totaliza o que já veio informado no XML da NFSe (tag `vRetIRRF` etc.) ou nas
> colunas opcionais da planilha. Se um imposto não foi informado, ele fica
> **em branco ("-")** no relatório — nenhum cálculo é feito para ele. A
> corretude dos valores informados na origem é de responsabilidade do emissor
> da nota / do profissional fiscal.

## Estrutura

```
.
├── setup.ps1 / run.ps1 / build-exe.ps1   # Scripts de apoio (Windows)
├── requirements.txt                      # Dependências de execução
├── requirements-dev.txt                  # + testes e empacotamento (.exe)
├── exemplos/
│   └── notas_modelo.csv                  # Planilha padrão de exemplo
├── src/
│   ├── gui.py                            # Interface gráfica (Tkinter)
│   ├── main.py                           # Linha de comando (CLI)
│   └── retencoes/
│       ├── config.py                     # Alíquotas e regras (parametrizáveis)
│       ├── models.py                     # Modelos de domínio
│       ├── sanitizacao.py                # Limpeza e classificação CNPJ/CPF (RF02)
│       ├── calculo.py                    # Motor de cálculo (RF03)
│       ├── pipeline.py                   # Orquestração ingestão→cálculo→relatório
│       ├── ingestao/                     # Leitura de CSV/XLSX e XML NFSe (RF01)
│       └── relatorios/                   # Agregação + exportação Excel (RF04/RF05)
└── tests/                                # Suíte de testes (pytest)
```

## Pré-requisitos
- **Windows** com **Python 3.10+** instalado (testado em 3.13).

## Instalação (ambiente local)

Na primeira vez, crie o ambiente virtual e instale as dependências.
**Jeito mais fácil:** dê **duplo-clique** em `setup.bat`.

Para desenvolver (testes + gerar `.exe`), use `setup.bat dev` (pelo prompt) ou:

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1 -Dev
```

> Os arquivos `.bat` são atalhos clicáveis; os `.ps1` fazem o trabalho de fato.

## Como usar

### Opção A — Interface gráfica (recomendada)
Dê **duplo-clique** em `run.bat` (ou rode `run.ps1` pelo PowerShell).

Na janela: selecione o **arquivo** (ou **pasta**) das notas, escolha onde salvar,
ajuste os parâmetros se quiser e clique em **Gerar relatório**.

### Opção B — Linha de comando
```powershell
.\.venv\Scripts\python.exe src\main.py -e exemplos\notas_modelo.csv -s saida\retencoes.xlsx
```

Para escolher o formato, use `-f excel|pdf|ambos` (ou deixe `auto`, que deduz
pela extensão de `--saida`):
```powershell
.\.venv\Scripts\python.exe src\main.py -e exemplos\notas_modelo.csv -s saida\retencoes -f ambos
```

### Entrada aceita (RF01)
- **XML** de NFSe nos padrões **ABRASF / Nacional** (`.xml`).
- **Planilha padrão** `.csv` / `.xlsx` (fallback para municípios sem XML).
- Uma **pasta** contendo vários arquivos — todos são lidos e consolidados.

Colunas da planilha padrão (nomes flexíveis, com ou sem acento/maiúsculas):
`numero`, `documento` (CNPJ/CPF), `nome` (opcional), `data` (emissão), `valor`
e, **opcionalmente**, `irrf`, `crf`, `inss` — os valores de retenção **já
informados**. Se essas três colunas não existirem (ou a célula estiver vazia),
nenhum cálculo é feito para aquele imposto naquela nota. A `data` aceita
formatos BR (`15/07/2026`) ou ISO (`2026-07-15`) e é usada no **acúmulo de
IRRF por dia**.

## Parâmetros do cálculo

| CLI | GUI | Descrição | Default |
|---|---|---|---|
| `--minimo` | Mínimo p/ retenção | Dispensa abaixo desse valor | `10.00` |

> A **identificação do prestador** não é digitada: é **extraída do XML** da NFSe
> e exibida no cabeçalho. Em planilhas (sem prestador), o cabeçalho fica em branco.

## Gerar o executável (.exe) — RNF01

Com as dependências de dev instaladas (`setup.bat dev`), dê **duplo-clique** em
`build-exe.bat` (ou rode `build-exe.ps1` pelo PowerShell).

Gera `dist\calculo-retencoes.exe` — um único arquivo, com GUI, que **roda em
qualquer Windows sem Python instalado**.

### Release automático (GitHub Actions)

Ao publicar uma **tag de versão**, o CI compila o `.exe` no Windows e cria uma
**Release** do GitHub com o executável anexado:

```bash
git tag v1.0.0
git push origin v1.0.0
```

O executável fica disponível na aba **Releases** do repositório.

## Rodar os testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Regras de negócio implementadas

- **Classificação:** documento sanitizado (só dígitos) e validado pelos dígitos
  verificadores → `CNPJ` (14), `CPF` (11) ou `Sem documento`.
- **Somente tomador Pessoa Jurídica (CNPJ) sofre retenção.** Pessoa Física (CPF)
  e notas sem documento **nunca retêm** (IRRF = CRF = INSS = 0).
- **O software não calcula por alíquota — só totaliza o que já foi informado**
  na origem (tag `vRetIRRF` do XML Nacional, ou colunas `irrf`/`crf`/`inss` da
  planilha). Se um imposto não foi informado, o relatório mostra `-` (não
  confundir com `R$ 0,00`, que significa "informado e dispensado/zero").
  - **CRF/INSS informados:** dispensados (zerados) quando abaixo do mínimo (R$ 10,00).
  - **IRRF informado — acúmulo por data (sempre ativo):** a 1ª avaliação é a
    **data**; somam apenas notas do mesmo CNPJ emitidas no **mesmo dia**. Se a
    soma do dia atingir R$ 10,00, mantém o IRRF informado de cada nota; senão,
    dispensa (zera). Datas diferentes não somam; notas sem data são avaliadas
    isoladamente; notas sem IRRF informado nunca entram na soma.
- **XML Nacional (`sped.fazenda.gov.br/nfse`):** o tomador é lido de `<toma>` e
  o prestador de `<emit>`/`<prest>` — não confundir um com o outro (bug corrigido
  nesta versão: o parser antigo pegava o CNPJ do prestador quando o layout não
  usava as tags "Tomador"/"Prestador" do ABRASF).
