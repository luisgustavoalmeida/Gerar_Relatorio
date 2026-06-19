"""Barra de menus e diálogos acionados pelos menus Arquivo, Revisão, Horas e Ajuda."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, simpledialog
from typing import TYPE_CHECKING, Any, Callable

import customtkinter as ctk

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
from rdo_diario.gui.menu_barra import EntradaMenuBarra, MenuSuspensoCtk, criar_barra_menu_ctk
from rdo_diario.gui.tema import opcoes_texto_tk_embutido
from rdo_diario.paths import (
    ARQUIVO_CONFIG_REGRAS_HORAS_JSON,
    ARQUIVO_MANUAL_AJUDA_JSON,
    ARQUIVO_SOBRE_AJUDA_JSON,
    PASTA_DADOS_RDO,
    PASTA_SAIDA_RELATORIOS_EXCEL,
    PASTA_TEMPLATE,
)

if TYPE_CHECKING:
    from rdo_diario.gui.app import AplicacaoRdo


class MixinMenu:
    """Menus principais, ajuda e ações de ficheiros/pastas."""

    _documento_atual: dict[str, Any] | None
    _data_em_edicao: Any
    _config_regras_horas: dict[str, Any]

    def _montar_barra_menu(self) -> None:
        """Barra de menus CustomTkinter (listas suspensas arredondadas)."""
        self._menus_ctk: list[MenuSuspensoCtk] = []
        self._barra_menu_frame, self._menus_ctk = criar_barra_menu_ctk(
            self,
            [
                ("Arquivo", self._itens_menu_arquivo()),
                ("Revisão", self._itens_menu_revisao()),
                ("Horas", self._itens_menu_horas()),
                ("Exibir", self._itens_menu_exibir()),
                ("Ajuda", self._itens_menu_ajuda()),
            ],
        )

    def _atualizar_barra_menu_tema(self) -> None:
        """Fecha listas abertas e atualiza a barra após troca de tema."""
        from rdo_diario.gui.tema import COR_FUNDO_SECUNDARIO

        for menu in getattr(self, "_menus_ctk", []):
            menu.fechar()
        if getattr(self, "_barra_menu_frame", None) is not None:
            self._barra_menu_frame.configure(fg_color=COR_FUNDO_SECUNDARIO)

    def _itens_menu_arquivo(self) -> list[EntradaMenuBarra]:
        return [
            EntradaMenuBarra("Salvar agora", self._salvar_documento_agora),
            EntradaMenuBarra("Novo cliente", self._abrir_dialogo_novo_cliente),
            EntradaMenuBarra(
                "Limpar informações do dia em edição",
                self._limpar_informacoes_dia_em_edicao,
            ),
            EntradaMenuBarra("Excluir cliente", self._excluir_cliente_atual),
            EntradaMenuBarra.sep(),
            EntradaMenuBarra(
                "Gerar Excel — mês em edição (RDO/FT)",
                self._gerar_relatorios_excel_mes_em_edicao,
            ),
            EntradaMenuBarra(
                "Gerar Excel — todos os meses (RDO/FT)",
                self._gerar_relatorios_excel_todos_meses,
            ),
            EntradaMenuBarra("Abrir pasta relatórios", self._abrir_pasta_relatorios),
            EntradaMenuBarra.sep(),
            EntradaMenuBarra("Salvar modelo de cabeçalho", self._salvar_modelo_cabecalho),
            EntradaMenuBarra("Carregar modelo de cabeçalho", self._carregar_modelo_cabecalho),
            EntradaMenuBarra.sep(),
            EntradaMenuBarra("Abrir Templates", self._abrir_pasta_templates),
            EntradaMenuBarra("Abrir dados (.json)", self._abrir_pasta_dados_json),
        ]

    def _itens_menu_revisao(self) -> list[EntradaMenuBarra]:
        return [
            EntradaMenuBarra(
                "Verificar ortografia e gramática agora",
                self._verificar_ortografia_todos_campos_relatorio,
            ),
            EntradaMenuBarra("Dicionário pessoal", self._abrir_dialogo_dicionario_ortografia),
            EntradaMenuBarra(
                "Sobre a verificação ortográfica",
                self._mostrar_info_verificacao_ortografia,
            ),
        ]

    def _itens_menu_horas(self) -> list[EntradaMenuBarra]:
        return [
            EntradaMenuBarra("Editar regras de horas e feriados", self._abrir_editor_regras_horas),
            EntradaMenuBarra(
                "Sincronizar feriados nacionais",
                self._dialogo_sincronizar_feriados_brasil,
            ),
            EntradaMenuBarra(
                "Copiar relatório detalhado do mês (métricas)",
                self._copiar_relatorio_metricas_mes,
            ),
            EntradaMenuBarra.sep(),
            EntradaMenuBarra(
                "Abrir pasta do arquivo de regras",
                self._abrir_pasta_config_regras_horas,
            ),
        ]

    def _itens_menu_exibir(self) -> list[EntradaMenuBarra]:
        return [
            EntradaMenuBarra("Alternar tema claro/escuro", self._alternar_tema_aplicacao),
        ]

    def _itens_menu_ajuda(self) -> list[EntradaMenuBarra]:
        return [
            EntradaMenuBarra("Manual", self._mostrar_manual_ajuda),
            EntradaMenuBarra("Sobre", self._mostrar_sobre_ajuda),
        ]

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
        topo = ctk.CTkToplevel(self)
        topo.title(titulo_janela)
        topo.transient(self)
        topo.geometry("760x620")
        topo.minsize(520, 400)
        ctk.CTkLabel(
            topo,
            text=str(caminho),
            font=ctk.CTkFont(size=11),
            text_color=("#666666", "#AAAAAA"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 4))
        corpo = ctk.CTkFrame(topo, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=12, pady=(0, 4))
        texto = scrolledtext.ScrolledText(
            corpo,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=8,
            pady=8,
            **opcoes_texto_tk_embutido(),
        )
        texto.pack(fill="both", expand=True)
        configurar_tags_texto_ajuda(texto)
        preencher(texto, doc)
        texto.configure(state=tk.DISABLED)
        ctk.CTkButton(topo, text="Fechar", command=topo.destroy).pack(pady=12)

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
        topo = ctk.CTkToplevel(self)
        topo.title("Regras de horas (JSON)")
        topo.transient(self)
        topo.geometry("720x560")
        ctk.CTkLabel(
            topo,
            text=str(ARQUIVO_CONFIG_REGRAS_HORAS_JSON),
            font=ctk.CTkFont(size=11),
            text_color=("#444444", "#AAAAAA"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 4))
        corpo = ctk.CTkFrame(topo, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=12, pady=(0, 4))
        texto = scrolledtext.ScrolledText(
            corpo,
            wrap=tk.NONE,
            font=("Consolas", 10),
            undo=True,
            **opcoes_texto_tk_embutido(),
        )
        texto.pack(fill="both", expand=True)
        try:
            texto.insert("1.0", json.dumps(self._config_regras_horas, ensure_ascii=False, indent=2))
        except (TypeError, ValueError):
            texto.insert("1.0", "{}")

        botoes = ctk.CTkFrame(topo, fg_color="transparent")
        botoes.pack(fill="x", padx=12, pady=12)

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

        ctk.CTkButton(botoes, text="Guardar e fechar", command=guardar).pack(side="right")
        ctk.CTkButton(botoes, text="Cancelar", command=topo.destroy).pack(side="right", padx=(0, 8))

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
