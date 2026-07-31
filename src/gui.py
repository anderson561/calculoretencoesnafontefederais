"""Interface gráfica simples (Tkinter) da Calculadora de Retenções Federais.

Permite selecionar um arquivo (.xml/.csv/.xlsx) ou uma pasta, definir o local de
saída e os parâmetros de cálculo, e gerar o relatório em PDF com um clique.

Não depende de bibliotecas externas de GUI (Tkinter faz parte da biblioteca
padrão do Python), o que facilita o empacotamento em .exe.
"""
from __future__ import annotations

import sys
import threading
import webbrowser
from decimal import Decimal, InvalidOperation
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Permite rodar como script solto (PyInstaller) ou como módulo do pacote.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from retencoes.atualizacao import InfoAtualizacao, verificar_atualizacao  # type: ignore
    from retencoes.config import ParametrosRetencao  # type: ignore
    from retencoes.pipeline import processar  # type: ignore
else:  # pragma: no cover
    from .retencoes.atualizacao import InfoAtualizacao, verificar_atualizacao
    from .retencoes.config import ParametrosRetencao
    from .retencoes.pipeline import processar

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
        self.var_saida = tk.StringVar(value=str(Path("saida") / "retencoes.pdf"))
        self.var_minimo = tk.StringVar(value=str(padrao.valor_minimo_retencao))

        self._montar_widgets()
        self._iniciar_verificacao_atualizacao()

    # ---- construção da interface -------------------------------------------------
    def _montar_widgets(self) -> None:
        self.lbl_atualizacao = tk.Label(
            self,
            text="",
            fg="#1A73E8",
            font=("", 9, "underline"),
            cursor="hand2",
        )
        self.lbl_atualizacao.bind("<Button-1>", self._abrir_link_atualizacao)

        r = 1
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

        # Parâmetros
        r += 1
        params = ttk.LabelFrame(self, text="Parâmetros de cálculo", padding=10)
        params.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(14, 6))
        params.columnconfigure(1, weight=1)

        ttk.Label(params, text="Mínimo p/ retenção (R$)").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(params, textvariable=self.var_minimo, width=12).grid(row=0, column=1, sticky="w")

        ttk.Label(
            params,
            text=(
                "Só tomador CNPJ sofre retenção. Só soma imposto já informado no "
                "XML/planilha (não aplica alíquota). IRRF acumulado por dia."
            ),
            foreground="#666666",
            wraplength=420,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

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
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="retencoes.pdf",
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
            valor_minimo_retencao=dec(self.var_minimo, "Mínimo"),
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

        # Processa em thread para não congelar a interface.
        self.btn_gerar.config(state="disabled")
        self.var_status.set("Processando…")
        threading.Thread(
            target=self._processar,
            args=(entrada, saida, parametros),
            daemon=True,
        ).start()

    def _processar(
        self, entrada: str, saida: str, parametros: ParametrosRetencao,
    ) -> None:
        try:
            gerados, qtd, qtd_substituidas = processar(entrada, saida, parametros)
        except Exception as exc:  # noqa: BLE001 — feedback amigável ao usuário
            self.master.after(0, self._falhou, exc)
        else:
            self.master.after(0, self._concluiu, gerados, qtd, qtd_substituidas)

    def _concluiu(self, gerados: list[Path], qtd: int, qtd_substituidas: int) -> None:
        self.btn_gerar.config(state="normal")
        lista = "\n".join(str(c) for c in gerados)
        self.var_status.set(f"{qtd} nota(s) processada(s). {len(gerados)} arquivo(s) gerado(s).")
        aviso_substituidas = (
            f"\n\n{qtd_substituidas} nota(s) substituída(s) excluída(s) do total (evita duplicidade)."
            if qtd_substituidas
            else ""
        )
        messagebox.showinfo(
            TITULO,
            f"{qtd} nota(s) processada(s) com sucesso!\n\nArquivo(s) gerado(s):\n{lista}{aviso_substituidas}",
        )

    def _falhou(self, exc: Exception) -> None:
        self.btn_gerar.config(state="normal")
        self.var_status.set("Falha ao processar.")
        messagebox.showerror(TITULO, f"Erro ao processar:\n{exc}")

    # ---- verificação de atualização (opcional, não bloqueia se offline) ----------
    def _iniciar_verificacao_atualizacao(self) -> None:
        self._info_atualizacao: InfoAtualizacao | None = None
        threading.Thread(target=self._verificar_atualizacao, daemon=True).start()

    def _verificar_atualizacao(self) -> None:
        info = verificar_atualizacao()
        if info is not None:
            self.master.after(0, self._mostrar_atualizacao, info)

    def _mostrar_atualizacao(self, info: InfoAtualizacao) -> None:
        self._info_atualizacao = info
        self.lbl_atualizacao.config(
            text=f"Nova versão disponível: v{info.versao_disponivel} "
            f"(atual: v{info.versao_atual}) — clique para baixar"
        )
        self.lbl_atualizacao.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

    def _abrir_link_atualizacao(self, evento: object = None) -> None:
        if self._info_atualizacao is not None:
            webbrowser.open(self._info_atualizacao.url_download)


def main() -> int:
    raiz = tk.Tk()
    raiz.title(TITULO)
    raiz.minsize(560, 360)
    App(raiz)
    raiz.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
