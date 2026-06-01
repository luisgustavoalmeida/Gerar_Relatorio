"""Janela principal: orquestra menu, formulário, calendário e ortografia."""

from __future__ import annotations

import json
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from rdo_diario.config_horas import (
    carregar_config_regras_horas,
    garantir_arquivo_config_regras_existe,
)
from rdo_diario.dicionario_ortografia_usuario import conjunto_para_filtragem
from rdo_diario.gerar_excel_relatorios import (
    gerar_relatorios_excel,
    remover_saida_relatorios_excel_cliente,
)
from rdo_diario.gui.calendario import MixinCalendario
from rdo_diario.gui.formulario_dia import MixinFormularioDia
from rdo_diario.gui.menu import MixinMenu
from rdo_diario.gui.ortografia import MixinOrtografia
from rdo_diario.gui.combo_suspenso import configurar_combo_ctk_aprimorado
from rdo_diario.gui.icone_janela import aplicar_icone_janela, preparar_icone_processo_windows
from rdo_diario.gui.tema import (
    COR_BORDA,
    COR_FUNDO,
    COR_FUNDO_CARD,
    COR_FUNDO_SECUNDARIO,
    COR_TEXTO,
    COR_TEXTO_SECUNDARIO,
    FONT_DICA_ABA,
    FONT_CONTAGEM_MES,
    FONT_DATA_SELECIONADA,
    FONT_INTERFACE,
    FONT_METRICAS,
    ALTURA_JANELA,
    LARGURA_JANELA,
    RAIO_BORDA,
    alternar_tema,
    configurar_aparencia,
    configurar_estilo_ttk,
    forcar_redesenho_tema,
    obter_cores_tema,
    configurar_abas_tabview,
    opcoes_tabview_ctk,
    opcoes_combo_ctk,
    opcoes_campo_entrada_ctk,
    texto_interno_campo,
)
from rdo_diario.horario_util import (
    texto_duracao_permitido_na_digitacao,
    texto_horario_permitido_na_digitacao,
)
from rdo_diario.paths import (
    ARQUIVO_MODELO_CABECALHO_JSON,
    PASTA_DADOS_RDO,
    garantir_pastas_executavel,
)
from rdo_diario.schema import (
    CAMPOS_JSON_CABECALHO,
    CHAVE_JSON_CONTRATANTE,
    CHAVE_JSON_NATUREZA_SERVICO,
    ROTULOS_CABECALHO,
)
from rdo_diario.storage import (
    carregar_documento_json,
    carregar_ou_criar_cliente,
    excluir_cliente_do_disco,
    listar_clientes_salvos,
    obter_documento_cliente_inicial,
    salvar_documento_json,
    salvar_memoria_ultimo_cliente,
)


class AplicacaoRdo(
    ctk.CTk,
    MixinMenu,
    MixinCalendario,
    MixinFormularioDia,
    MixinOrtografia,
):
    """Janela principal: seleção de cliente, abas de dados fixos e relatório diário."""

    def __init__(self) -> None:
        super().__init__()
        aplicar_icone_janela(self)
        configurar_estilo_ttk(self)
        self.title("Relatório de atividades diárias")
        self.geometry(f"{LARGURA_JANELA}x{ALTURA_JANELA}")
        self.minsize(980, 600)

        self._documento_atual: dict[str, Any] | None = None
        self._caminho_arquivo_atual: Path | None = None
        self._data_em_edicao: date = date.today()
        self._widgets_cabecalho: dict[str, ctk.CTkEntry] = {}
        self._widgets_campos_dia: dict[str, ctk.CTkTextbox] = {}
        self._widgets_tempo_atividade: dict[str, ctk.CTkEntry] = {}
        self._widgets_horarios: dict[str, ctk.CTkEntry] = {}
        self._id_agendamento_salvar: str | None = None
        self._widget_calendario = None
        self._combo_selecao_cliente: ctk.CTkComboBox | None = None
        self._mapa_rotulo_para_caminho: dict[str, Path] = {}
        self._rotulo_texto_data = None
        self._rotulo_data_atual = None
        self._rotulo_contagem_mes = None
        self._comando_validacao_entrada_hora = None
        self._comando_validacao_entrada_duracao = None
        self._ortografia_timers_por_widget: dict[int, str] = {}
        self._ortografia_job_id_por_widget: dict[int, int] = {}
        self._ortografia_alvos_por_widget: dict[int, list[dict[str, Any]]] = {}
        self._conjunto_dicionario_ortografia: set[str] = conjunto_para_filtragem()
        self._config_regras_horas: dict[str, Any] = carregar_config_regras_horas()
        self._rotulo_metricas_dia = None
        self._rotulo_metricas_mes = None
        self._barra_cliente: ctk.CTkFrame | None = None
        self._rotulo_barra_cliente: ctk.CTkLabel | None = None
        self._tabview: ctk.CTkTabview | None = None

        self._montar_barra_menu()
        self._montar_barra_cliente()
        self._comando_validacao_entrada_hora = self.register(
            lambda proposta: texto_horario_permitido_na_digitacao(proposta)
        )
        self._comando_validacao_entrada_duracao = self.register(
            lambda proposta: texto_duracao_permitido_na_digitacao(proposta)
        )
        self._montar_corpo_janela()

        self.protocol("WM_DELETE_WINDOW", self._ao_fechar_janela)
        self.after(200, self._inicializar_apos_abrir)

    def refresh_apos_tema(self) -> None:
        """Atualiza widgets ttk/tk embutidos após troca claro/escuro."""
        configurar_estilo_ttk(self)
        self._atualizar_barra_menu_tema()
        self._atualizar_barra_cliente_tema()
        cores = obter_cores_tema()
        for texto in self._widgets_campos_dia.values():
            texto.configure(
                border_color=COR_BORDA,
                fg_color=COR_FUNDO_CARD,
                text_color=COR_TEXTO,
            )
            texto_interno_campo(texto).tag_configure(
                self.TAG_ERRO_ORTOGRAFIA,
                foreground=cores["erro"],
            )
        for entrada in (
            *self._widgets_horarios.values(),
            *self._widgets_tempo_atividade.values(),
            *self._widgets_cabecalho.values(),
        ):
            entrada.configure(
                border_color=COR_BORDA,
                fg_color=COR_FUNDO_CARD,
                text_color=COR_TEXTO,
            )
        if self._rotulo_texto_data is not None:
            self._rotulo_texto_data.configure(font=FONT_DATA_SELECIONADA, text_color=COR_TEXTO)
        if self._rotulo_data_atual is not None:
            self._rotulo_data_atual.configure(font=FONT_DATA_SELECIONADA, text_color=COR_TEXTO)
        if self._rotulo_contagem_mes is not None:
            self._rotulo_contagem_mes.configure(
                font=FONT_CONTAGEM_MES,
                text_color=COR_TEXTO_SECUNDARIO,
            )
        if self._rotulo_metricas_dia is not None:
            self._rotulo_metricas_dia.configure(font=FONT_METRICAS, text_color=COR_TEXTO)
        if self._rotulo_metricas_mes is not None:
            self._rotulo_metricas_mes.configure(font=FONT_METRICAS, text_color=COR_TEXTO)
        if self._widget_calendario:
            from rdo_diario.gui.calendario import aplicar_cores_tema_calendario

            aplicar_cores_tema_calendario(self._widget_calendario, compacto=True)
            self._atualizar_marcadores_calendario()
        if self._tabview is not None:
            self._tabview.configure(**opcoes_tabview_ctk())
            configurar_abas_tabview(self._tabview)

    def _alternar_tema_aplicacao(self) -> None:
        alternar_tema()
        forcar_redesenho_tema(self)

    def _montar_barra_cliente(self) -> None:
        """Barra superior: seleção de cliente (contratante + natureza)."""
        self._barra_cliente = ctk.CTkFrame(
            self,
            fg_color=COR_FUNDO_SECUNDARIO,
            corner_radius=0,
        )
        self._barra_cliente.pack(fill="x", padx=0, pady=0)
        conteudo = ctk.CTkFrame(self._barra_cliente, fg_color="transparent")
        conteudo.pack(fill="x", padx=8, pady=8)
        self._rotulo_barra_cliente = ctk.CTkLabel(
            conteudo,
            text="Cliente (contratante + natureza):",
            font=FONT_INTERFACE,
        )
        self._rotulo_barra_cliente.pack(side="left", padx=(0, 6))
        self._combo_selecao_cliente = ctk.CTkComboBox(
            conteudo,
            state="readonly",
            command=self._ao_trocar_cliente_combo,
            **opcoes_combo_ctk(largura=520),
        )
        configurar_combo_ctk_aprimorado(self._combo_selecao_cliente)
        self._combo_selecao_cliente.pack(side="left", fill="x", expand=True, padx=4)

    def _atualizar_barra_cliente_tema(self) -> None:
        if self._barra_cliente is not None:
            self._barra_cliente.configure(fg_color=COR_FUNDO_SECUNDARIO)
        if self._combo_selecao_cliente is not None:
            self._combo_selecao_cliente.configure(**opcoes_combo_ctk(largura=520))
            self._combo_selecao_cliente.update()

    def _montar_corpo_janela(self) -> None:
        """Abas «Dados fixos» e «Relatórios», com calendário na segunda."""
        self._tabview = ctk.CTkTabview(self, **opcoes_tabview_ctk())
        self._tabview.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._tabview.add("Cabeçalhos")
        self._tabview.add("Relatórios de trabalho")
        configurar_abas_tabview(self._tabview)
        aba_cabecalho = self._tabview.tab("Cabeçalhos")
        aba_registros = self._tabview.tab("Relatórios de trabalho")

        dica_cab = ctk.CTkLabel(
            aba_cabecalho,
            text="Informações destinadas aos cabeçalhos das planilhas (RDO e FT).",
            font=FONT_DICA_ABA,
            text_color=COR_TEXTO_SECUNDARIO,
            wraplength=800,
            justify="left",
        )
        dica_cab.pack(fill="x", padx=8, pady=(8, 4))
        area_rolavel = ctk.CTkScrollableFrame(
            aba_cabecalho,
            fg_color=COR_FUNDO,
            corner_radius=RAIO_BORDA,
        )
        area_rolavel.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        form_cab = ctk.CTkFrame(area_rolavel, fg_color="transparent")
        form_cab.pack(fill="both", expand=True, padx=4, pady=4)
        for indice, campo in enumerate(CAMPOS_JSON_CABECALHO):
            ctk.CTkLabel(form_cab, text=ROTULOS_CABECALHO[campo] + ":", anchor="w", font=FONT_INTERFACE).grid(
                row=indice, column=0, sticky="nw", pady=6, padx=(0, 10)
            )
            entrada = ctk.CTkEntry(form_cab, width=480, **opcoes_campo_entrada_ctk())
            entrada.grid(row=indice, column=1, sticky="ew", pady=6)
            entrada.bind("<KeyRelease>", self._agendar_salvamento_automatico)
            self._widgets_cabecalho[campo] = entrada
        form_cab.columnconfigure(1, weight=1)

        painel = ctk.CTkFrame(aba_registros, fg_color="transparent")
        painel.pack(fill="both", expand=True, padx=4, pady=8)
        painel.grid_columnconfigure(0, weight=4)
        painel.grid_columnconfigure(1, weight=0)
        painel.grid_rowconfigure(0, weight=1)

        coluna_formulario = ctk.CTkFrame(painel, fg_color="transparent")
        coluna_calendario = ctk.CTkFrame(painel, fg_color="transparent", width=280)
        coluna_formulario.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        coluna_calendario.grid(row=0, column=1, sticky="n")

        self._montar_coluna_formulario_dia(coluna_formulario)
        self._montar_coluna_calendario(coluna_calendario)

    def _inicializar_apos_abrir(self) -> None:
        """Primeira carga: combo, documento inicial, data de hoje e marcas no calendário."""
        inicial = obter_documento_cliente_inicial()
        self._atualizar_lista_combo_clientes()
        if inicial is None:
            self._atualizar_rotulo_contagem_relatorios_mes()
            self._atualizar_marcadores_calendario()
            messagebox.showinfo(
                "Primeiro uso",
                "Crie um cliente com Arquivo → Novo cliente…. "
                "A chave do arquivo é contratante + natureza do serviço.",
            )
            return
        documento, caminho = inicial
        self._documento_atual = documento
        self._caminho_arquivo_atual = caminho
        self._marcar_combo_cliente_atual(documento)
        self._carregar_cabecalho_no_formulario()
        chave = documento.get("chave") or {}
        salvar_memoria_ultimo_cliente(
            str(chave.get(CHAVE_JSON_CONTRATANTE, "")),
            str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")),
        )
        self._data_em_edicao = date.today()
        if self._widget_calendario:
            self._widget_calendario.selection_set(self._data_em_edicao)
        self._atualizar_rotulo_data_selecionada()
        self._carregar_registro_dia_no_formulario(self._data_em_edicao)
        self._atualizar_marcadores_calendario()

    def _atualizar_lista_combo_clientes(self) -> None:
        """Reconstrói a lista do combobox a partir dos ficheiros em `dados_rdo`."""
        self._mapa_rotulo_para_caminho.clear()
        itens = listar_clientes_salvos()
        rotulos: list[str] = []
        for contratante, natureza, caminho in itens:
            rotulo = f"{contratante} — {natureza}" if contratante and natureza else (
                contratante or natureza or caminho.name
            )
            rotulos.append(rotulo)
            self._mapa_rotulo_para_caminho[rotulo] = caminho
        if self._combo_selecao_cliente:
            self._combo_selecao_cliente.configure(values=rotulos if rotulos else [""])

    def _marcar_combo_cliente_atual(self, documento: dict[str, Any]) -> None:
        """Seleciona no combo o item correspondente ao documento carregado."""
        chave = documento.get("chave") or {}
        c = str(chave.get(CHAVE_JSON_CONTRATANTE, "")).strip()
        n = str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
        rotulo = f"{c} — {n}" if c and n else (c or n)
        if self._combo_selecao_cliente and rotulo in (self._combo_selecao_cliente.cget("values") or ()):
            self._combo_selecao_cliente.set(rotulo)

    def _ao_trocar_cliente_combo(self, _valor: str | None = None) -> None:
        """Troca de cliente: grava o dia atual, abre o novo JSON e recarrega o formulário."""
        if not self._combo_selecao_cliente:
            return
        rotulo = self._combo_selecao_cliente.get().strip()
        caminho = self._mapa_rotulo_para_caminho.get(rotulo)
        if not caminho or not caminho.is_file():
            return
        self._persistir_dia_atual_no_documento()
        self._salvar_documento_agora()
        self._documento_atual = carregar_documento_json(caminho)
        self._caminho_arquivo_atual = caminho
        chave = self._documento_atual.get("chave") or {}
        salvar_memoria_ultimo_cliente(
            str(chave.get(CHAVE_JSON_CONTRATANTE, "")),
            str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")),
        )
        self._carregar_cabecalho_no_formulario()
        self._carregar_registro_dia_no_formulario(self._data_em_edicao)
        if self._widget_calendario:
            self._widget_calendario.selection_set(self._data_em_edicao)
        self._atualizar_marcadores_calendario()

    def _abrir_dialogo_novo_cliente(self) -> None:
        """Diálogo modal para criar contratante + natureza e abrir o ficheiro novo."""
        topo = ctk.CTkToplevel(self)
        topo.title("Novo cliente")
        topo.transient(self)
        topo.grab_set()
        topo.geometry("520x200")
        ctk.CTkLabel(topo, text="Contratante (chave):").grid(row=0, column=0, sticky="w", padx=12, pady=8)
        entrada_contratante = ctk.CTkEntry(topo, width=320)
        entrada_contratante.grid(row=0, column=1, padx=12, pady=8)
        ctk.CTkLabel(topo, text="Natureza do serviço (chave):").grid(
            row=1, column=0, sticky="w", padx=12, pady=8
        )
        entrada_natureza = ctk.CTkEntry(topo, width=320)
        entrada_natureza.grid(row=1, column=1, padx=12, pady=8)

        def confirmar() -> None:
            c = entrada_contratante.get().strip()
            n = entrada_natureza.get().strip()
            if not c or not n:
                messagebox.showwarning("Validação", "Preencha contratante e natureza do serviço.", parent=topo)
                return
            self._persistir_dia_atual_no_documento()
            self._salvar_documento_agora()
            documento, caminho = carregar_ou_criar_cliente(c, n)
            self._documento_atual = documento
            self._caminho_arquivo_atual = caminho
            salvar_memoria_ultimo_cliente(c, n)
            self._atualizar_lista_combo_clientes()
            self._marcar_combo_cliente_atual(documento)
            self._carregar_cabecalho_no_formulario()
            self._carregar_registro_dia_no_formulario(self._data_em_edicao)
            if self._widget_calendario:
                self._widget_calendario.selection_set(self._data_em_edicao)
            self._atualizar_marcadores_calendario()
            topo.destroy()

        ctk.CTkButton(topo, text="Criar e abrir", command=confirmar).grid(
            row=2, column=0, columnspan=2, pady=16
        )

    def _excluir_cliente_atual(self) -> None:
        """Remove o cliente aberto: JSON, relatórios Excel e atualiza a interface."""
        if not self._documento_atual or not self._caminho_arquivo_atual:
            messagebox.showwarning(
                "Excluir cliente",
                "Não há cliente aberto para excluir.\n\n"
                "Selecione um cliente na lista ou crie um novo.",
                parent=self,
            )
            return

        chave = self._documento_atual.get("chave") or {}
        contratante = str(chave.get(CHAVE_JSON_CONTRATANTE, "")).strip()
        natureza = str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
        rotulo = f"{contratante} — {natureza}" if contratante and natureza else (
            contratante or natureza or self._caminho_arquivo_atual.name
        )

        if not messagebox.askyesno(
            "Excluir cliente",
            f"Excluir permanentemente o cliente:\n\n{rotulo}\n\n"
            "Serão removidos o ficheiro JSON com todos os registos diários "
            "e os relatórios Excel gerados (RDO/FT).\n\n"
            "Esta ação não pode ser desfeita.",
            parent=self,
            icon="warning",
        ):
            return

        documento_excluido = self._documento_atual
        caminho_excluido = self._caminho_arquivo_atual

        if self._id_agendamento_salvar:
            self.after_cancel(self._id_agendamento_salvar)
            self._id_agendamento_salvar = None

        try:
            remover_saida_relatorios_excel_cliente(documento_excluido)
            excluir_cliente_do_disco(
                caminho_excluido,
                contratante=contratante,
                natureza_servico=natureza,
            )
        except OSError as erro:
            messagebox.showerror("Excluir cliente", str(erro), parent=self)
            return

        self._documento_atual = None
        self._caminho_arquivo_atual = None
        self._atualizar_lista_combo_clientes()

        proximo = obter_documento_cliente_inicial()
        if proximo:
            documento, caminho = proximo
            self._documento_atual = documento
            self._caminho_arquivo_atual = caminho
            self._marcar_combo_cliente_atual(documento)
            chave_nova = documento.get("chave") or {}
            salvar_memoria_ultimo_cliente(
                str(chave_nova.get(CHAVE_JSON_CONTRATANTE, "")),
                str(chave_nova.get(CHAVE_JSON_NATUREZA_SERVICO, "")),
            )
            self._carregar_cabecalho_no_formulario()
            self._carregar_registro_dia_no_formulario(self._data_em_edicao)
        else:
            if self._combo_selecao_cliente:
                self._combo_selecao_cliente.set("")
            for widget in self._widgets_cabecalho.values():
                widget.delete(0, "end")
            self._preencher_formulario_com_registro_dia({})
            for widget in self._widgets_horarios.values():
                widget.delete(0, "end")
            self._atualizar_rotulo_jornada_liquida()
            self._atualizar_rotulo_contagem_relatorios_mes()

        if self._widget_calendario:
            self._widget_calendario.selection_set(self._data_em_edicao)
        self._atualizar_marcadores_calendario()
        self.title("Relatório de atividades diárias")

        messagebox.showinfo(
            "Excluir cliente",
            f"O cliente «{rotulo}» foi excluído.",
            parent=self,
        )

    def _carregar_cabecalho_no_formulario(self) -> None:
        """Copia `cabecalho_fixo` do documento para os campos da primeira aba."""
        if not self._documento_atual:
            return
        cabecalho = self._documento_atual.get("cabecalho_fixo") or {}
        for campo, widget in self._widgets_cabecalho.items():
            widget.delete(0, "end")
            widget.insert(0, str(cabecalho.get(campo, "") or ""))

    def _copiar_cabecalho_formulario_para_documento(self) -> None:
        """Grava no documento em memória os valores atuais dos campos do cabeçalho."""
        if not self._documento_atual:
            return
        cabecalho = dict(self._documento_atual.get("cabecalho_fixo") or {})
        for campo, widget in self._widgets_cabecalho.items():
            cabecalho[campo] = widget.get().strip()
        self._documento_atual["cabecalho_fixo"] = cabecalho

    def _cabecalho_formulario_tem_valores_preenchidos(self) -> bool:
        """Indica se algum campo do cabeçalho no formulário contém texto."""
        return any(widget.get().strip() for widget in self._widgets_cabecalho.values())

    def _agendar_salvamento_automatico(self, _evento: tk.Event | None = None) -> None:
        """Agenda salvamento após um curto atraso (debounce) para não gravar a cada tecla."""
        self._atualizar_rotulo_contagem_relatorios_mes()
        self._atualizar_marcadores_calendario()
        if self._id_agendamento_salvar:
            self.after_cancel(self._id_agendamento_salvar)
        self._id_agendamento_salvar = self.after(1200, self._executar_salvamento_automatico)

    def _executar_salvamento_automatico(self) -> None:
        """Callback do timer: salva sem messagebox de erro visível (silencioso)."""
        self._id_agendamento_salvar = None
        self._salvar_documento_agora(silencioso=True)

    def _salvar_documento_agora(self, silencioso: bool = False) -> None:
        """Persiste documento completo no disco e atualiza memória do último cliente."""
        if not self._documento_atual or not self._caminho_arquivo_atual:
            return
        self._persistir_dia_atual_no_documento()
        self._copiar_cabecalho_formulario_para_documento()
        chave = self._documento_atual.get("chave") or {}
        salvar_memoria_ultimo_cliente(
            str(chave.get(CHAVE_JSON_CONTRATANTE, "")),
            str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")),
        )
        try:
            salvar_documento_json(self._caminho_arquivo_atual, self._documento_atual)
        except OSError as erro:
            if not silencioso:
                messagebox.showerror("Salvar", str(erro))
            return
        self._atualizar_marcadores_calendario()
        self._atualizar_rotulo_contagem_relatorios_mes()
        if not silencioso:
            self.title(f"Relatório de atividades diárias — salvo {datetime.now().strftime('%H:%M:%S')}")

    def _salvar_modelo_cabecalho(self) -> None:
        """Salva os dados atuais do cabeçalho em um arquivo JSON modelo na pasta template."""
        if not self._documento_atual:
            messagebox.showwarning(
                "Modelo de cabeçalho",
                "Abra um cliente primeiro para salvar o modelo do cabeçalho.",
                parent=self,
            )
            return
        cabecalho = dict(self._documento_atual.get("cabecalho_fixo") or {})
        for campo, widget in self._widgets_cabecalho.items():
            cabecalho[campo] = widget.get().strip()

        try:
            salvar_documento_json(ARQUIVO_MODELO_CABECALHO_JSON, cabecalho)
            messagebox.showinfo(
                "Modelo de cabeçalho",
                f"Modelo de cabeçalho salvo com sucesso em:\n\n{ARQUIVO_MODELO_CABECALHO_JSON}",
                parent=self,
            )
        except OSError as erro:
            messagebox.showerror("Salvar modelo", str(erro), parent=self)

    def _carregar_modelo_cabecalho(self) -> None:
        """Carrega um modelo de cabeçalho do arquivo JSON e preenche o formulário."""
        if not ARQUIVO_MODELO_CABECALHO_JSON.exists():
            messagebox.showwarning(
                "Modelo de cabeçalho",
                f"Arquivo de modelo não encontrado:\n\n{ARQUIVO_MODELO_CABECALHO_JSON}\n\n"
                "Primeiro, salve um modelo usando «Salvar modelo de cabeçalho».",
                parent=self,
            )
            return

        try:
            modelo = carregar_documento_json(ARQUIVO_MODELO_CABECALHO_JSON)
        except (OSError, json.JSONDecodeError) as erro:
            messagebox.showerror(
                "Carregar modelo",
                f"Erro ao ler arquivo de modelo:\n{erro}",
                parent=self,
            )
            return

        if not isinstance(modelo, dict):
            messagebox.showerror(
                "Carregar modelo",
                "Arquivo de modelo inválido (não é um dicionário JSON).",
                parent=self,
            )
            return

        if self._cabecalho_formulario_tem_valores_preenchidos():
            if not messagebox.askyesno(
                "Carregar modelo de cabeçalho",
                "Os campos de cabeçalho já contêm informações preenchidas.\n\n"
                "Deseja substituí-las pelos valores do modelo salvo?\n\n"
                "Os dados atuais serão perdidos.",
                parent=self,
                icon="warning",
            ):
                return

        for campo, widget in self._widgets_cabecalho.items():
            valor = str(modelo.get(campo, "") or "")
            widget.delete(0, "end")
            widget.insert(0, valor)

        if self._documento_atual:
            self._documento_atual["cabecalho_fixo"] = dict(modelo)

        messagebox.showinfo(
            "Modelo de cabeçalho",
            "O formulário de cabeçalho foi atualizado com os valores do modelo.",
            parent=self,
        )

        self._agendar_salvamento_automatico()

    def _gerar_relatorios_excel(self) -> None:
        """Gera ou atualiza os ficheiros RDO e FT por mês na pasta `saida_relatorios`."""
        if not self._documento_atual or not self._caminho_arquivo_atual:
            messagebox.showwarning(
                "Gerar Excel",
                "Não há documento carregado. Selecione ou crie um cliente antes de gerar os relatórios.",
            )
            return
        self._persistir_dia_atual_no_documento()
        self._copiar_cabecalho_formulario_para_documento()
        try:
            self._salvar_documento_agora(silencioso=True)
            caminhos = gerar_relatorios_excel(self._documento_atual, self._caminho_arquivo_atual)
        except ValueError as e:
            messagebox.showwarning("Gerar Excel", str(e))
            return
        except OSError as e:
            messagebox.showerror("Gerar Excel", f"Erro ao gravar ficheiros:\n{e}")
            return
        except Exception as e:
            messagebox.showerror("Gerar Excel", f"Não foi possível gerar os relatórios:\n{e}")
            return
        linhas = "\n".join(str(p) for p in caminhos)
        messagebox.showinfo(
            "Gerar Excel",
            f"Foram criados ou atualizados {len(caminhos)} ficheiro(s):\n\n{linhas}",
        )

    def _ao_fechar_janela(self) -> None:
        """Salva em silêncio e encerra a aplicação."""
        try:
            self._salvar_documento_agora(silencioso=True)
        except Exception:
            pass
        self.destroy()


def iniciar_aplicacao() -> None:
    """Garante a pasta de dados e abre a janela principal."""
    preparar_icone_processo_windows()
    garantir_pastas_executavel()
    configurar_aparencia()
    PASTA_DADOS_RDO.mkdir(parents=True, exist_ok=True)
    garantir_arquivo_config_regras_existe()
    app = AplicacaoRdo()
    app.mainloop()
