# Calculadora e Totalizadora de Retenções Federais (NFSe)

[![CI](https://github.com/anderson561/calculoretencoesnafontefederais/actions/workflows/ci.yml/badge.svg)](https://github.com/anderson561/calculoretencoesnafontefederais/actions/workflows/ci.yml)

Aplicação **Windows / Python** que processa lotes de Notas Fiscais de Serviço
Eletrônica (NFSe), calcula as retenções federais na fonte (**IRRF**, **CRF** =
PIS/COFINS/CSLL e **INSS**) e gera dois relatórios em Excel:

1. **Sintético** — totais por tipo de tomador (CNPJ / CPF / Sem documento).
2. **Analítico** — totais por tomador individual (blocos de CNPJ, CPF e sem documento).

Os relatórios podem ser exportados em **Excel (.xlsx)**, **PDF** ou **ambos**.

A aplicação roda **100% local e offline** (adequado a dados fiscais sensíveis /
LGPD), com **interface gráfica** e também linha de comando.

> ⚠️ **Aviso fiscal:** as alíquotas e regras são *defaults* parametrizáveis e
> refletem o descrito no PRD. Elas **devem ser validadas por profissional fiscal**
> contra a legislação vigente. O software apenas aplica os parâmetros configurados.

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
`numero`, `documento` (CNPJ/CPF), `nome` (opcional), `data` (emissão) e `valor`.
A `data` aceita formatos BR (`15/07/2026`) ou ISO (`2026-07-15`) e é usada no
**acúmulo de IRRF por dia**.

## Parâmetros do cálculo

| CLI | GUI | Descrição | Default |
|---|---|---|---|
| `--irrf` | IRRF (fração) | Alíquota de IRRF | `0.015` |
| `--inss` | INSS (fração) | Alíquota de INSS | `0.11` |
| `--minimo` | Mínimo p/ retenção | Dispensa abaixo desse valor | `10.00` |
| `--teto-inss` | Teto INSS | Teto da base do INSS (0 = sem teto) | `0` |

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
- **Cálculo (tomador CNPJ):** IRRF, CRF (PIS 0,65% + COFINS 3% + CSLL 1% = 4,65%) e INSS.
  - **CRF/INSS:** dispensados quando abaixo do mínimo (R$ 10,00). INSS respeita o
    **teto previdenciário** quando configurado.
  - **IRRF — acúmulo por data (sempre ativo):** a 1ª avaliação é a **data**; somam
    apenas notas do mesmo CNPJ emitidas no **mesmo dia**. Se a soma do dia atingir
    R$ 10,00, retém cada nota; senão, dispensa. Datas diferentes não somam; notas
    sem data são avaliadas isoladamente.
