"""Barra de menus e diálogos acionados pelos menus Arquivo, Revisão, Horas e Ajuda."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, simpledialog, ttk
from typing import TYPE_CHECKING, Any, Callable

from rdo_diario.ajuda_conteudo import (
    carregar_documento_ajuda,
    configurar_tags_texto_ajuda,
    preencher_widget_manual,
    preencher_widget_sobre,
)
from rdo_diario.calculo_metricas_horas import gerar_relatorio_metricas_mes_texto
from rdo_diario.config_horas import (
    carregar_config_regras_horas,
    salvar_config_regras_horas,
    sincronizar_feriados_brasil,
)
from rdo_diario.paths import (
    ARQUIVO_CONFIG_REGRAS_HORAS_JSON,
    ARQUIVO_MANUAL_AJUDA_JSON,
    ARQUIVO_SOBRE_AJUDA_JSON,
    PASTA_DADOS_RDO,
    PASTA_SAIDA_RELATORIOS_EXCEL,
    PASTA_TEMPLATE,
)
from rdo_diario.storage import carregar_documento_json

if TYPE_CHECKING:
    from rdo_diario.gui.app import AplicacaoRdo


class MixinMenu:
    """Menus principais, ajuda e ações de ficheiros/pastas."""

    _documento_atual: dict[str, Any] | None
    _data_em_edicao: Any
    _config_regras_horas: dict[str, Any]

    def _montar_barra_menu(self) -> None:
        """Cria os menus «Arquivo» e «Revisão»."""
        barra_menu = tk.Menu(self)
        menu_arquivo = tk.Menu(barra_menu, tearoff=0)
        menu_arquivo.add_command(
            label="Novo cliente…",
            command=self._abrir_dialogo_novo_cliente,
        )
        menu_arquivo.add_command(label="Salvar agora", command=self._salvar_documento_agora)
        menu_arquivo.add_command(
            label="Gerar Excel (RDO/FT)",
            command=self._gerar_relatorios_excel,
        )
        menu_arquivo.add_separator()
        menu_arquivo.add_command(
            label="Limpar informações do dia em edição…",
            command=self._limpar_informacoes_dia_em_edicao,
        )
        menu_arquivo.add_separator()
        menu_arquivo.add_command(
            label="Salvar modelo de cabeçalho…",
            command=self._salvar_modelo_cabecalho,
        )
        menu_arquivo.add_command(
            label="Carregar modelo de cabeçalho…",
            command=self._carregar_modelo_cabecalho,
        )
        menu_arquivo.add_separator()
        menu_arquivo.add_command(
            label="Abrir pasta relatórios",
            command=self._abrir_pasta_relatorios,
        )
        menu_arquivo.add_command(
            label="Abrir Templates",
            command=self._abrir_pasta_templates,
        )
        menu_arquivo.add_command(
            label="Abrir dados .json",
            command=self._abrir_pasta_dados_json,
        )
        barra_menu.add_cascade(label="Arquivo", menu=menu_arquivo)
        menu_revisao = tk.Menu(barra_menu, tearoff=0)
        menu_revisao.add_command(
            label="Verificar ortografia e gramática agora",
            command=self._verificar_ortografia_todos_campos_relatorio,
        )
        menu_revisao.add_command(
            label="Dicionário pessoal (palavras e siglas)…",
            command=self._abrir_dialogo_dicionario_ortografia,
        )
        menu_revisao.add_command(
            label="Sobre a verificação ortográfica…",
            command=self._mostrar_info_verificacao_ortografia,
        )
        barra_menu.add_cascade(label="Revisão", menu=menu_revisao)
        menu_horas = tk.Menu(barra_menu, tearoff=0)
        menu_horas.add_command(
            label="Editar regras de horas (JSON)…",
            command=self._abrir_editor_regras_horas,
        )
        menu_horas.add_command(
            label="Sincronizar feriados nacionais (Brasil)…",
            command=self._dialogo_sincronizar_feriados_brasil,
        )
        menu_horas.add_command(
            label="Copiar relatório detalhado do mês (métricas)…",
            command=self._copiar_relatorio_metricas_mes,
        )
        menu_horas.add_separator()
        menu_horas.add_command(
            label="Abrir pasta do ficheiro de regras…",
            command=self._abrir_pasta_config_regras_horas,
        )
        barra_menu.add_cascade(label="Horas", menu=menu_horas)
        menu_ajuda = tk.Menu(barra_menu, tearoff=0)
        menu_ajuda.add_command(label="Manual", command=self._mostrar_manual_ajuda)
        menu_ajuda.add_command(label="Sobre", command=self._mostrar_sobre_ajuda)
        barra_menu.add_cascade(label="Ajuda", menu=menu_ajuda)
        self.config(menu=barra_menu)

    def _mostrar_dialogo_conteudo_ajuda(
        self,
        caminho: Path,
        preencher: Callable[[Any, dict[str, Any]], None],
        titulo_padrao: str,
    ) -> None:
        """Abre janela com texto formatado a partir de um JSON em template/."""
        try:
            doc = carregar_documento_ajuda(caminho)
        except FileNotFoundError:
            messagebox.showerror(
                "Ajuda",
                f"Ficheiro não encontrado:\n\n{caminho}",
                parent=self,
            )
            return
        except (json.JSONDecodeError, ValueError, OSError) as erro:
            messagebox.showerror(
                "Ajuda",
                f"Não foi possível ler o conteúdo:\n\n{erro}",
                parent=self,
            )
            return
        titulo_janela = str(doc.get("titulo", titulo_padrao) or titulo_padrao).strip()
        topo = tk.Toplevel(self)
        topo.title(titulo_janela)
        topo.transient(self)
        topo.geometry("760x620")
        topo.minsize(520, 400)
        ttk.Label(
            topo,
            text=str(caminho),
            font=("Segoe UI", 8),
            foreground="#666666",
        ).pack(fill=tk.X, padx=10, pady=(8, 4))
        corpo = ttk.Frame(topo, padding=(10, 0))
        corpo.pack(fill=tk.BOTH, expand=True)
        texto = scrolledtext.ScrolledText(
            corpo,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=8,
            pady=8,
        )
        texto.pack(fill=tk.BOTH, expand=True)
        configurar_tags_texto_ajuda(texto)
        preencher(texto, doc)
        texto.configure(state=tk.DISABLED)
        ttk.Button(topo, text="Fechar", command=topo.destroy).pack(pady=10)

    def _mostrar_manual_ajuda(self) -> None:
        self._mostrar_dialogo_conteudo_ajuda(
            ARQUIVO_MANUAL_AJUDA_JSON,
            preencher_widget_manual,
            "Manual",
        )

    def _mostrar_sobre_ajuda(self) -> None:
        self._mostrar_dialogo_conteudo_ajuda(
            ARQUIVO_SOBRE_AJUDA_JSON,
            preencher_widget_sobre,
            "Sobre",
        )

    def _abrir_editor_regras_horas(self: AplicacaoRdo) -> None:
        """Janela com o JSON de regras para edição manual."""
        self._config_regras_horas = carregar_config_regras_horas()
        topo = tk.Toplevel(self)
        topo.title("Regras de horas (JSON)")
        topo.transient(self)
        topo.geometry("720x560")
        ttk.Label(
            topo,
            text=str(ARQUIVO_CONFIG_REGRAS_HORAS_JSON),
            font=("Segoe UI", 8),
            foreground="#444444",
        ).pack(fill=tk.X, padx=8, pady=(8, 4))
        corpo = ttk.Frame(topo, padding=(8, 0))
        corpo.pack(fill=tk.BOTH, expand=True)
        texto = scrolledtext.ScrolledText(
            corpo,
            wrap=tk.NONE,
            font=("Consolas", 10),
            undo=True,
        )
        texto.pack(fill=tk.BOTH, expand=True)
        try:
            texto.insert("1.0", json.dumps(self._config_regras_horas, ensure_ascii=False, indent=2))
        except (TypeError, ValueError):
            texto.insert("1.0", "{}")

        botoes = ttk.Frame(topo, padding=8)
        botoes.pack(fill=tk.X)

        def guardar() -> None:
            bruto = texto.get("1.0", "end-1c")
            try:
                doc = json.loads(bruto)
            except json.JSONDecodeError as erro:
                messagebox.showerror("JSON inválido", str(erro), parent=topo)
                return
            if not isinstance(doc, dict):
                messagebox.showerror("JSON inválido", "O ficheiro deve ser um objeto JSON «{…}».", parent=topo)
                return
            try:
                salvar_config_regras_horas(doc)
            except OSError as erro:
                messagebox.showerror("Gravar", str(erro), parent=topo)
                return
            self._config_regras_horas = carregar_config_regras_horas()
            self._atualizar_painel_metricas_horas()
            self._atualizar_marcadores_calendario()
            messagebox.showinfo("Regras de horas", "Alterações gravadas.", parent=topo)
            topo.destroy()

        ttk.Button(botoes, text="Guardar e fechar", command=guardar).pack(side=tk.RIGHT)
        ttk.Button(botoes, text="Cancelar", command=topo.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _dialogo_sincronizar_feriados_brasil(self: AplicacaoRdo) -> None:
        """Pede o ano central e sincroniza feriados BR (ano−1, ano, ano+1)."""
        padrao = self._data_em_edicao.year
        ano = simpledialog.askinteger(
            "Feriados nacionais (Brasil)",
            "Ano de referência (serão atualizados também o ano anterior e o seguinte):",
            initialvalue=padrao,
            minvalue=2000,
            maxvalue=2100,
            parent=self,
        )
        if ano is None:
            return
        anos = sorted({ano - 1, ano, ano + 1})
        try:
            novo = sincronizar_feriados_brasil(self._config_regras_horas, anos)
            salvar_config_regras_horas(novo)
        except RuntimeError as erro:
            messagebox.showerror("Sincronizar feriados", str(erro), parent=self)
            return
        except OSError as erro:
            messagebox.showerror("Gravar", str(erro), parent=self)
            return
        self._config_regras_horas = carregar_config_regras_horas()
        self._atualizar_painel_metricas_horas()
        self._atualizar_marcadores_calendario()
        messagebox.showinfo(
            "Feriados",
            f"Feriados nacionais atualizados para os anos {anos[0]}, {anos[1]} e {anos[2]}.",
            parent=self,
        )

    def _copiar_relatorio_metricas_mes(self: AplicacaoRdo) -> None:
        """Gera texto com todas as linhas do mês da data selecionada e copia para a área de transferência."""
        if not self._documento_atual:
            messagebox.showinfo("Relatório", "Abra um cliente primeiro.", parent=self)
            return
        regs = self._registros_diarios_efetivos_para_contagem()
        a, m = self._data_em_edicao.year, self._data_em_edicao.month
        texto = gerar_relatorio_metricas_mes_texto(regs, a, m, self._config_regras_horas)
        try:
            self.clipboard_clear()
            self.clipboard_append(texto)
            self.update()
        except tk.TclError as erro:
            messagebox.showerror("Área de transferência", str(erro), parent=self)
            return
        messagebox.showinfo(
            "Relatório",
            f"Texto do mês {m:02d}/{a} copiado para a área de transferência.",
            parent=self,
        )

    def _abrir_pasta_no_explorador(self, pasta: Path, *, criar_se_ausente: bool = True) -> None:
        """Abre a pasta no explorador do sistema (cria-a se pedido e não existir)."""
        try:
            if criar_se_ausente:
                pasta.mkdir(parents=True, exist_ok=True)
            elif not pasta.is_dir():
                messagebox.showerror(
                    "Abrir pasta",
                    f"A pasta não existe:\n\n{pasta}",
                    parent=self,
                )
                return
            if sys.platform == "win32":
                os.startfile(pasta)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(pasta)], check=False)
            else:
                subprocess.run(["xdg-open", str(pasta)], check=False)
        except OSError as erro:
            messagebox.showerror("Abrir pasta", str(erro), parent=self)

    def _abrir_pasta_relatorios(self) -> None:
        """Abre `saida_relatorios/` (relatórios Excel gerados)."""
        self._abrir_pasta_no_explorador(PASTA_SAIDA_RELATORIOS_EXCEL)

    def _abrir_pasta_templates(self) -> None:
        """Abre `template/` (modelos e configurações)."""
        self._abrir_pasta_no_explorador(PASTA_TEMPLATE, criar_se_ausente=False)

    def _abrir_pasta_dados_json(self) -> None:
        """Abre `dados_rdo/` (JSON por cliente)."""
        self._abrir_pasta_no_explorador(PASTA_DADOS_RDO)

    def _abrir_pasta_config_regras_horas(self) -> None:
        """Abre a pasta `template/` (ficheiro de regras de horas)."""
        self._abrir_pasta_no_explorador(ARQUIVO_CONFIG_REGRAS_HORAS_JSON.parent, criar_se_ausente=False)
