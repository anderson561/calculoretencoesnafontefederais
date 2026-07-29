"""Interface gráfica simples (Tkinter) da Calculadora de Retenções Federais.

Permite selecionar um arquivo (.xml/.csv/.xlsx) ou uma pasta, definir o local de
saída e os parâmetros de cálculo, e gerar os relatórios em Excel com um clique.

Não depende de bibliotecas externas de GUI (Tkinter faz parte da biblioteca
padrão do Python), o que facilita o empacotamento em .exe.
"""
from __future__ import annotations

import sys
import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Permite rodar como script solto (PyInstaller) ou como módulo do pacote.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from retencoes.config import ParametrosRetencao  # type: ignore
    from retencoes.models import Cabecalho  # type: ignore
    from retencoes.pipeline import processar  # type: ignore
    from retencoes.sanitizacao import cnpj_valido  # type: ignore
else:  # pragma: no cover
    from .retencoes.config import ParametrosRetencao
    from .retencoes.models import Cabecalho
    from .retencoes.pipeline import processar
    from .retencoes.sanitizacao import cnpj_valido

TITULO = "Calculadora de Retenções Federais (NFSe)"


class App(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=16)
        self.master = master
        self.grid(sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        padrao = ParametrosRetencao()
        self.var_entrada = tk.StringVar()
        self.var_saida = tk.StringVar(value=str(Path("saida") / "retencoes.xlsx"))
        self.var_irrf = tk.StringVar(value=str(padrao.aliquota_irrf))
        self.var_inss = tk.StringVar(value=str(padrao.aliquota_inss))
        self.var_minimo = tk.StringVar(value=str(padrao.valor_minimo_retencao))
        self.var_teto = tk.StringVar(value=str(padrao.teto_inss))
        self.var_crf_pf = tk.BooleanVar(value=not padrao.crf_isento_para_pf)
        self.var_irrf_acumulo = tk.BooleanVar(value=padrao.irrf_dispensa_por_acumulo)
        self.var_formato = tk.StringVar(value="excel")
        self.var_empresa = tk.StringVar()
        self.var_cnpj = tk.StringVar()
        self.var_competencia = tk.StringVar()

        self._montar_widgets()

    # ---- construção da interface -------------------------------------------------
    def _montar_widgets(self) -> None:
        r = 0
        ttk.Label(self, text="1) Entrada (arquivo XML/CSV/XLSX ou pasta)").grid(
            row=r, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        r += 1
        ttk.Entry(self, textvariable=self.var_entrada, width=52).grid(
            row=r, column=0, columnspan=2, sticky="ew", padx=(0, 8)
        )
        botoes = ttk.Frame(self)
        botoes.grid(row=r, column=2, sticky="e")
        ttk.Button(botoes, text="Arquivo…", command=self._escolher_arquivo).grid(row=0, column=0, padx=2)
        ttk.Button(botoes, text="Pasta…", command=self._escolher_pasta).grid(row=0, column=1, padx=2)

        r += 1
        ttk.Label(self, text="2) Salvar relatório em").grid(
            row=r, column=0, columnspan=3, sticky="w", pady=(12, 4)
        )
        r += 1
        ttk.Entry(self, textvariable=self.var_saida, width=52).grid(
            row=r, column=0, columnspan=2, sticky="ew", padx=(0, 8)
        )
        ttk.Button(self, text="Salvar como…", command=self._escolher_saida).grid(
            row=r, column=2, sticky="e"
        )

        # Identificação (cabeçalho do relatório)
        r += 1
        ident = ttk.LabelFrame(self, text="Identificação (cabeçalho do relatório)", padding=10)
        ident.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(14, 6))
        ident.columnconfigure(1, weight=1)
        ttk.Label(ident, text="Empresa").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(ident, textvariable=self.var_empresa).grid(
            row=0, column=1, columnspan=3, sticky="ew"
        )
        ttk.Label(ident, text="CNPJ").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(ident, textvariable=self.var_cnpj, width=22).grid(row=1, column=1, sticky="w")
        ttk.Label(ident, text="Competência (mm/aaaa)").grid(row=1, column=2, sticky="w", padx=4)
        ttk.Entry(ident, textvariable=self.var_competencia, width=12).grid(row=1, column=3, sticky="w")

        # Parâmetros
        r += 1
        params = ttk.LabelFrame(self, text="Parâmetros de cálculo", padding=10)
        params.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(14, 6))
        params.columnconfigure(1, weight=1)
        params.columnconfigure(3, weight=1)

        ttk.Label(params, text="IRRF (fração)").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(params, textvariable=self.var_irrf, width=12).grid(row=0, column=1, sticky="w")
        ttk.Label(params, text="INSS (fração)").grid(row=0, column=2, sticky="w", padx=4)
        ttk.Entry(params, textvariable=self.var_inss, width=12).grid(row=0, column=3, sticky="w")

        ttk.Label(params, text="Mínimo p/ retenção (R$)").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(params, textvariable=self.var_minimo, width=12).grid(row=1, column=1, sticky="w")
        ttk.Label(params, text="Teto INSS (0 = sem teto)").grid(row=1, column=2, sticky="w", padx=4)
        ttk.Entry(params, textvariable=self.var_teto, width=12).grid(row=1, column=3, sticky="w")

        ttk.Checkbutton(
            params, text="Aplicar CRF também para Pessoa Física", variable=self.var_crf_pf
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        ttk.Checkbutton(
            params, text="Dispensa de IRRF por acúmulo (soma por tomador)",
            variable=self.var_irrf_acumulo,
        ).grid(row=3, column=0, columnspan=4, sticky="w")

        # Formato de saída
        r += 1
        formato = ttk.LabelFrame(self, text="Formato do relatório", padding=10)
        formato.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(4, 6))
        for i, (rotulo, valor) in enumerate(
            (("Excel (.xlsx)", "excel"), ("PDF (.pdf)", "pdf"), ("Ambos", "ambos"))
        ):
            ttk.Radiobutton(
                formato, text=rotulo, value=valor, variable=self.var_formato
            ).grid(row=0, column=i, sticky="w", padx=(0, 16))

        # Ação
        r += 1
        self.btn_gerar = ttk.Button(self, text="Gerar relatório", command=self._ao_gerar)
        self.btn_gerar.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(8, 6), ipady=4)

        # Status
        r += 1
        self.var_status = tk.StringVar(value="Pronto.")
        ttk.Label(self, textvariable=self.var_status, foreground="#1F4E78").grid(
            row=r, column=0, columnspan=3, sticky="w"
        )

    # ---- callbacks de seleção ----------------------------------------------------
    def _escolher_arquivo(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo de notas",
            filetypes=[("Notas (XML/CSV/Excel)", "*.xml *.csv *.xlsx *.xls"), ("Todos", "*.*")],
        )
        if caminho:
            self.var_entrada.set(caminho)

    def _escolher_pasta(self) -> None:
        caminho = filedialog.askdirectory(title="Selecione a pasta com as notas")
        if caminho:
            self.var_entrada.set(caminho)

    def _escolher_saida(self) -> None:
        caminho = filedialog.asksaveasfilename(
            title="Salvar relatório como",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="retencoes.xlsx",
        )
        if caminho:
            self.var_saida.set(caminho)

    # ---- processamento -----------------------------------------------------------
    def _ler_parametros(self) -> ParametrosRetencao:
        def dec(var: tk.StringVar, nome: str) -> Decimal:
            try:
                return Decimal(var.get().strip().replace(",", "."))
            except InvalidOperation as exc:
                raise ValueError(f"Valor inválido em '{nome}': {var.get()!r}") from exc

        return ParametrosRetencao(
            aliquota_irrf=dec(self.var_irrf, "IRRF"),
            aliquota_inss=dec(self.var_inss, "INSS"),
            valor_minimo_retencao=dec(self.var_minimo, "Mínimo"),
            teto_inss=dec(self.var_teto, "Teto INSS"),
            crf_isento_para_pf=not self.var_crf_pf.get(),
            irrf_dispensa_por_acumulo=self.var_irrf_acumulo.get(),
        )

    def _ao_gerar(self) -> None:
        entrada = self.var_entrada.get().strip()
        saida = self.var_saida.get().strip()
        if not entrada:
            messagebox.showwarning(TITULO, "Selecione um arquivo ou pasta de entrada.")
            return
        if not Path(entrada).exists():
            messagebox.showerror(TITULO, f"Entrada não encontrada:\n{entrada}")
            return
        if not saida:
            messagebox.showwarning(TITULO, "Defina onde salvar o relatório.")
            return
        try:
            parametros = self._ler_parametros()
        except ValueError as exc:
            messagebox.showerror(TITULO, str(exc))
            return

        # Valida o CNPJ do cabeçalho (opcional): se preenchido e inválido, confirma.
        cnpj = self.var_cnpj.get().strip()
        if cnpj and not cnpj_valido(cnpj):
            if not messagebox.askyesno(
                TITULO,
                f"O CNPJ do cabeçalho parece inválido:\n{cnpj}\n\nGerar o relatório mesmo assim?",
            ):
                return

        # Processa em thread para não congelar a interface.
        formato = self.var_formato.get()
        cabecalho = Cabecalho(
            empresa=self.var_empresa.get().strip(),
            cnpj=cnpj,
            competencia=self.var_competencia.get().strip(),
        )
        self.btn_gerar.config(state="disabled")
        self.var_status.set("Processando…")
        threading.Thread(
            target=self._processar,
            args=(entrada, saida, parametros, formato, cabecalho),
            daemon=True,
        ).start()

    def _processar(
        self, entrada: str, saida: str, parametros: ParametrosRetencao,
        formato: str, cabecalho: Cabecalho,
    ) -> None:
        try:
            gerados, qtd = processar(entrada, saida, parametros, formato, cabecalho)
        except Exception as exc:  # noqa: BLE001 — feedback amigável ao usuário
            self.master.after(0, self._falhou, exc)
        else:
            self.master.after(0, self._concluiu, gerados, qtd)

    def _concluiu(self, gerados: list[Path], qtd: int) -> None:
        self.btn_gerar.config(state="normal")
        lista = "\n".join(str(c) for c in gerados)
        self.var_status.set(f"{qtd} nota(s) processada(s). {len(gerados)} arquivo(s) gerado(s).")
        messagebox.showinfo(
            TITULO,
            f"{qtd} nota(s) processada(s) com sucesso!\n\nArquivo(s) gerado(s):\n{lista}",
        )

    def _falhou(self, exc: Exception) -> None:
        self.btn_gerar.config(state="normal")
        self.var_status.set("Falha ao processar.")
        messagebox.showerror(TITULO, f"Erro ao processar:\n{exc}")


def main() -> int:
    raiz = tk.Tk()
    raiz.title(TITULO)
    raiz.minsize(560, 360)
    App(raiz)
    raiz.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
