"""Janela de configurações do assistente IA (Gemini)."""

from __future__ import annotations

import threading
from copy import deepcopy
from tkinter import messagebox
from uuid import uuid4

import customtkinter as ctk

from rdo_diario.gui.combo_suspenso import configurar_combo_ctk_aprimorado
from rdo_diario.gui.desfazer_refazer import (
    preparar_widget_edicao,
    registrar_desfazer_refazer_recursivo,
    reiniciar_historico_desfazer_widget,
)
from rdo_diario.gui.tema import (
    COR_ERRO,
    COR_FUNDO_SECUNDARIO,
    COR_PRIMARIA,
    COR_PRIMARIA_HOVER,
    COR_TEXTO_SECUNDARIO,
    FONT_DICA_ABA,
    FONT_GRUPO,
    FONT_INTERFACE,
    opcoes_caixa_texto_ctk,
    opcoes_campo_entrada_ctk,
    opcoes_combo_ctk,
    resolver_cor,
)
from rdo_diario.ia_service import listar_modelos_gemini, testar_modelo_gemini
from rdo_diario.ia_settings import (
    CAMPOS_CONTEXTO_CABECALHO,
    CAMPOS_CONTEXTO_CABECALHO_PADRAO,
    MODO_ROTACAO_FIXO,
    MODO_ROTACAO_RODIZIO,
    MODELOS_GEMINI_SUGERIDOS,
    carregar_config_ia,
    listar_chaves_gemini,
    nome_arquivo_importacao_chaves,
    obter_prompt_selecionado,
    rotulo_campo_contexto_cabecalho,
    salvar_chaves_gemini,
    salvar_config_ia,
)


class DialogoConfiguracoesIa(ctk.CTkToplevel):
    """Configura chaves, rotação, modelo, histórico e prompts."""

    _MAPA_ROTACAO = {
        "Conta fixa": MODO_ROTACAO_FIXO,
        "Rodízio a cada reescrita": MODO_ROTACAO_RODIZIO,
    }

    def __init__(self, master, *, ao_salvar=None) -> None:
        super().__init__(master)
        self.title("Configurações Gemini")
        self.geometry("840x780")
        self.minsize(720, 660)
        self.transient(master)
        self.grab_set()
        self._ao_salvar_callback = ao_salvar
        self._config = carregar_config_ia()
        self._prompts = deepcopy(self._config.get("prompts") or [])
        self._prompt_atual_id = str(obter_prompt_selecionado(self._config).get("id") or "")
        self._mapa_rotulos_chaves: dict[str, int] = {}
        self._chaves_cadastradas: list[str] = []
        self._modelos_disponiveis: list[str] = list(MODELOS_GEMINI_SUGERIDOS)
        self._atualizando_modelos = False
        self._testando_modelo = False
        self._montar()
        registrar_desfazer_refazer_recursivo(self)
        self.after(50, self._focar_janela)
        self.after(120, lambda: self._atualizar_modelos_api(silencioso=True))

    def _focar_janela(self) -> None:
        try:
            self.focus_force()
        except Exception:
            pass

    def _montar(self) -> None:
        ctk.CTkLabel(
            self,
            text="Configurações do assistente IA",
            font=FONT_GRUPO,
        ).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            self,
            text=(
                "As chaves Gemini ficam em template/.env. Os prompts editados, o modelo e o "
                "histórico ficam em template/config_usuario.json. O prompt de fábrica (usado "
                "na primeira execução e no .exe) está em template/prompt_ia_padrao.txt."
            ),
            font=FONT_DICA_ABA,
            text_color=COR_TEXTO_SECUNDARIO,
            justify="left",
            wraplength=780,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        corpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=16, pady=8)
        corpo.grid_columnconfigure(0, weight=1)
        corpo.grid_rowconfigure(3, weight=1)

        secao_chaves = ctk.CTkFrame(corpo)
        secao_chaves.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        secao_chaves.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(secao_chaves, text="Chaves Gemini", font=FONT_GRUPO).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        self.lbl_dica_chaves = ctk.CTkLabel(
            secao_chaves,
            text=(
                "Cadastre as chaves da API Google AI (Gemini). Com mais de uma chave, escolha "
                "«Rodízio a cada reescrita» em Execução. Se uma conta atingir limite (429/cota), "
                "o app pausa essa chave por um tempo e tenta a próxima."
            ),
            font=FONT_DICA_ABA,
            text_color=COR_TEXTO_SECUNDARIO,
            wraplength=700,
            justify="left",
            anchor="w",
        )
        self.lbl_dica_chaves.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self._secao_chaves = secao_chaves
        self._wrap_dica_chaves: int | None = None
        secao_chaves.bind("<Configure>", self._ajustar_wraplength_dica_chaves, add="+")
        moldura_lista = ctk.CTkFrame(
            secao_chaves,
            fg_color=resolver_cor(COR_FUNDO_SECUNDARIO),
            corner_radius=8,
        )
        moldura_lista.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        moldura_lista.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            moldura_lista,
            text="Chaves cadastradas",
            font=FONT_INTERFACE,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        self._scroll_chaves = ctk.CTkScrollableFrame(
            moldura_lista,
            height=132,
            fg_color="transparent",
        )
        self._scroll_chaves.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 10))
        self._scroll_chaves.grid_columnconfigure(0, weight=1)

        linha_nova_chave = ctk.CTkFrame(secao_chaves, fg_color="transparent")
        linha_nova_chave.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        linha_nova_chave.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(linha_nova_chave, text="Nova chave:", font=FONT_INTERFACE).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self.entry_nova_chave = ctk.CTkEntry(
            linha_nova_chave,
            placeholder_text="Cole a chave da API aqui",
            **opcoes_campo_entrada_ctk(),
        )
        preparar_widget_edicao(self.entry_nova_chave)
        self.entry_nova_chave.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.entry_nova_chave.bind("<Return>", lambda _e: self._adicionar_chave_ui())
        ctk.CTkButton(
            linha_nova_chave,
            text="Adicionar",
            width=110,
            fg_color=COR_PRIMARIA,
            hover_color=COR_PRIMARIA_HOVER,
            command=self._adicionar_chave_ui,
        ).grid(row=0, column=2, sticky="e")

        acoes_chaves = ctk.CTkFrame(secao_chaves, fg_color="transparent")
        acoes_chaves.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 10))
        acoes_chaves.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            acoes_chaves,
            text="Importar arquivo local",
            width=170,
            command=self._importar_arquivo_local,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            acoes_chaves,
            text=f"Arquivo: {nome_arquivo_importacao_chaves()}",
            font=FONT_DICA_ABA,
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.lbl_resumo_chaves = ctk.CTkLabel(
            secao_chaves,
            text="",
            font=FONT_DICA_ABA,
            text_color=COR_TEXTO_SECUNDARIO,
            justify="left",
        )
        self.lbl_resumo_chaves.grid(row=5, column=0, sticky="w", padx=12, pady=(0, 4))
        self._definir_chaves_cadastradas(listar_chaves_gemini(), atualizar_ui=True)

        secao_execucao = ctk.CTkFrame(corpo)
        secao_execucao.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        secao_execucao.grid_columnconfigure(1, weight=1)
        secao_execucao.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(secao_execucao, text="Execução", font=FONT_GRUPO).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(10, 6)
        )
        ctk.CTkLabel(secao_execucao, text="Modo de chave:", font=FONT_INTERFACE).grid(
            row=1, column=0, sticky="w", padx=(12, 8), pady=6
        )
        self.combo_modo_rotacao = ctk.CTkComboBox(
            secao_execucao,
            values=list(self._MAPA_ROTACAO.keys()),
            command=lambda _valor: self._atualizar_combo_chave_ativa(),
            **opcoes_combo_ctk(largura=260),
        )
        self.combo_modo_rotacao.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=6)
        configurar_combo_ctk_aprimorado(self.combo_modo_rotacao)
        self.combo_modo_rotacao.set(self._rotulo_modo(self._config.get("modo_rotacao")))
        ctk.CTkLabel(secao_execucao, text="Conta fixa ativa:", font=FONT_INTERFACE).grid(
            row=1, column=2, sticky="w", padx=(12, 8), pady=6
        )
        self.combo_chave_ativa = ctk.CTkComboBox(secao_execucao, values=["Sem chaves"], **opcoes_combo_ctk())
        self.combo_chave_ativa.grid(row=1, column=3, sticky="ew", padx=(0, 12), pady=6)
        configurar_combo_ctk_aprimorado(self.combo_chave_ativa)
        ctk.CTkLabel(secao_execucao, text="Modelo Gemini:", font=FONT_INTERFACE).grid(
            row=2, column=0, sticky="w", padx=(12, 8), pady=6
        )
        self.combo_modelo = ctk.CTkComboBox(
            secao_execucao,
            values=list(MODELOS_GEMINI_SUGERIDOS),
            **opcoes_combo_ctk(largura=260),
        )
        self.combo_modelo.grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=6)
        configurar_combo_ctk_aprimorado(self.combo_modelo)
        modelo_atual = str(self._config.get("modelo") or MODELOS_GEMINI_SUGERIDOS[0]).strip()
        self._aplicar_lista_modelos(list(MODELOS_GEMINI_SUGERIDOS), modelo_preferido=modelo_atual)
        ctk.CTkLabel(secao_execucao, text="Dias de histórico:", font=FONT_INTERFACE).grid(
            row=2, column=2, sticky="w", padx=(12, 8), pady=6
        )
        self.entry_dias_historico = ctk.CTkEntry(secao_execucao, **opcoes_campo_entrada_ctk(largura=110))
        self.entry_dias_historico.grid(row=2, column=3, sticky="w", padx=(0, 12), pady=6)
        self.entry_dias_historico.insert(0, str(int(self._config.get("dias_historico") or 0)))

        linha_modelos = ctk.CTkFrame(secao_execucao, fg_color="transparent")
        linha_modelos.grid(row=3, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 8))
        self.btn_atualizar_modelos = ctk.CTkButton(
            linha_modelos,
            text="Atualizar lista",
            width=140,
            command=lambda: self._atualizar_modelos_api(silencioso=False),
        )
        self.btn_atualizar_modelos.pack(side="left")
        self.btn_testar_modelo = ctk.CTkButton(
            linha_modelos,
            text="Testar modelo",
            width=130,
            fg_color=COR_PRIMARIA,
            hover_color=COR_PRIMARIA_HOVER,
            command=self._testar_modelo_selecionado,
        )
        self.btn_testar_modelo.pack(side="left", padx=(8, 0))
        self.lbl_modelo_info = ctk.CTkLabel(
            linha_modelos,
            text="A lista é preenchida pela API (models.list). Use «Atualizar lista» se mudar a chave.",
            font=FONT_DICA_ABA,
            text_color=COR_TEXTO_SECUNDARIO,
            justify="left",
            wraplength=520,
            anchor="w",
        )
        self.lbl_modelo_info.pack(side="left", padx=(12, 0), fill="x", expand=True)

        linha_checks = ctk.CTkFrame(secao_execucao, fg_color="transparent")
        linha_checks.grid(row=4, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 6))
        self.chk_primeiro = ctk.CTkCheckBox(
            linha_checks,
            text="Remover primeiro parágrafo do histórico",
            font=FONT_INTERFACE,
        )
        self.chk_primeiro.pack(side="left", padx=(0, 12))
        self.chk_ultimo = ctk.CTkCheckBox(
            linha_checks,
            text="Remover último parágrafo do histórico",
            font=FONT_INTERFACE,
        )
        self.chk_ultimo.pack(side="left")
        if bool(self._config.get("remover_primeiro_paragrafo")):
            self.chk_primeiro.select()
        if bool(self._config.get("remover_ultimo_paragrafo")):
            self.chk_ultimo.select()

        linha_min_chars = ctk.CTkFrame(secao_execucao, fg_color="transparent")
        linha_min_chars.grid(row=5, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 10))
        ctk.CTkLabel(
            linha_min_chars,
            text="Ignorar histórico com menos de:",
            font=FONT_INTERFACE,
        ).pack(side="left")
        self.entry_min_caracteres_historico = ctk.CTkEntry(
            linha_min_chars,
            **opcoes_campo_entrada_ctk(largura=90),
        )
        self.entry_min_caracteres_historico.pack(side="left", padx=(8, 6))
        self.entry_min_caracteres_historico.insert(
            0, str(int(self._config.get("minimo_caracteres_historico") or 0))
        )
        ctk.CTkLabel(
            linha_min_chars,
            text="caracteres (0 = não filtrar)",
            font=FONT_DICA_ABA,
            text_color=COR_TEXTO_SECUNDARIO,
        ).pack(side="left")

        secao_contexto = ctk.CTkFrame(corpo)
        secao_contexto.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        secao_contexto.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(secao_contexto, text="Contexto do cabeçalho no prompt", font=FONT_GRUPO).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        ctk.CTkLabel(
            secao_contexto,
            text=(
                "Marque os campos do cabeçalho do projeto que devem ser enviados no contexto da IA. "
                "Campos vazios no projeto são omitidos automaticamente."
            ),
            font=FONT_DICA_ABA,
            text_color=COR_TEXTO_SECUNDARIO,
            wraplength=760,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        barra_contexto = ctk.CTkFrame(secao_contexto, fg_color="transparent")
        barra_contexto.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        ctk.CTkButton(
            barra_contexto,
            text="Marcar todos",
            width=120,
            command=lambda: self._definir_checks_contexto_cabecalho(True),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            barra_contexto,
            text="Desmarcar todos",
            width=130,
            command=lambda: self._definir_checks_contexto_cabecalho(False),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            barra_contexto,
            text="Padrão",
            width=90,
            command=self._restaurar_checks_contexto_padrao,
        ).pack(side="left")

        grade_contexto = ctk.CTkFrame(secao_contexto, fg_color="transparent")
        grade_contexto.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        grade_contexto.grid_columnconfigure(0, weight=1)
        grade_contexto.grid_columnconfigure(1, weight=1)
        self._checks_contexto_cabecalho: dict[str, ctk.CTkCheckBox] = {}
        selecionados = set(self._config.get("campos_contexto_cabecalho") or CAMPOS_CONTEXTO_CABECALHO_PADRAO)
        for indice, campo in enumerate(CAMPOS_CONTEXTO_CABECALHO):
            check = ctk.CTkCheckBox(
                grade_contexto,
                text=rotulo_campo_contexto_cabecalho(campo),
                font=FONT_INTERFACE,
            )
            check.grid(row=indice // 2, column=indice % 2, sticky="w", padx=(0, 12), pady=3)
            if campo in selecionados:
                check.select()
            self._checks_contexto_cabecalho[campo] = check

        secao_prompts = ctk.CTkFrame(corpo)
        secao_prompts.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        secao_prompts.grid_columnconfigure(0, weight=1)
        secao_prompts.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(secao_prompts, text="Prompts do engenheiro", font=FONT_GRUPO).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )
        ctk.CTkLabel(
            secao_prompts,
            text="Escolha qual prompt global será usado na aba de IA. Você pode criar vários perfis de escrita.",
            font=FONT_DICA_ABA,
            text_color=COR_TEXTO_SECUNDARIO,
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        barra_prompt = ctk.CTkFrame(secao_prompts, fg_color="transparent")
        barra_prompt.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        barra_prompt.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(barra_prompt, text="Prompt:", font=FONT_INTERFACE).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self.combo_prompts = ctk.CTkComboBox(
            barra_prompt,
            values=self._nomes_prompts(),
            command=self._ao_trocar_prompt,
            **opcoes_combo_ctk(),
        )
        self.combo_prompts.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        configurar_combo_ctk_aprimorado(self.combo_prompts)
        botoes_prompt = ctk.CTkFrame(barra_prompt, fg_color="transparent")
        botoes_prompt.grid(row=0, column=2, sticky="e")
        ctk.CTkButton(botoes_prompt, text="Novo", width=80, command=self._novo_prompt).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(
            botoes_prompt, text="Duplicar", width=90, command=self._duplicar_prompt
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(botoes_prompt, text="Excluir", width=80, command=self._excluir_prompt).pack(side="left")

        editor = ctk.CTkFrame(secao_prompts, fg_color="transparent")
        editor.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        editor.grid_columnconfigure(0, weight=1)
        editor.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(editor, text="Nome do prompt:", font=FONT_INTERFACE).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.entry_nome_prompt = ctk.CTkEntry(editor, **opcoes_campo_entrada_ctk())
        self.entry_nome_prompt.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(editor, text="Texto do prompt:", font=FONT_INTERFACE).grid(
            row=2, column=0, sticky="w", pady=(0, 4)
        )
        self.txt_prompt = ctk.CTkTextbox(editor, **opcoes_caixa_texto_ctk(altura_px=300))
        preparar_widget_edicao(self.txt_prompt)
        self.txt_prompt.grid(row=3, column=0, sticky="nsew")
        if hasattr(self.master, "_ligar_ortografia_caixa"):
            self.master._ligar_ortografia_caixa(self.txt_prompt, autosave=False)

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(rodape, text="Cancelar", width=100, command=self.destroy).pack(
            side="right", padx=(8, 0)
        )
        ctk.CTkButton(
            rodape,
            text="Salvar",
            width=120,
            fg_color=COR_PRIMARIA,
            hover_color=COR_PRIMARIA_HOVER,
            command=self._salvar,
        ).pack(side="right")

        self._atualizar_combo_chave_ativa()
        self._carregar_prompt_no_editor(self._prompt_atual_id)

    def _ajustar_wraplength_dica_chaves(self, event) -> None:
        # Bind no frame pai (não no label): alterar wraplength no próprio label
        # dispara <Configure> de novo e causava RecursionError.
        if event.widget is not getattr(self, "_secao_chaves", None):
            return
        wrap = max(280, int(event.width) - 28)
        if self._wrap_dica_chaves == wrap:
            return
        self._wrap_dica_chaves = wrap
        self.lbl_dica_chaves.configure(wraplength=wrap)

    def _definir_checks_contexto_cabecalho(self, marcado: bool) -> None:
        for check in self._checks_contexto_cabecalho.values():
            if marcado:
                check.select()
            else:
                check.deselect()

    def _restaurar_checks_contexto_padrao(self) -> None:
        padrao = set(CAMPOS_CONTEXTO_CABECALHO_PADRAO)
        for campo, check in self._checks_contexto_cabecalho.items():
            if campo in padrao:
                check.select()
            else:
                check.deselect()

    def _campos_contexto_cabecalho_selecionados(self) -> list[str]:
        return [
            campo
            for campo in CAMPOS_CONTEXTO_CABECALHO
            if self._checks_contexto_cabecalho.get(campo) is not None
            and int(self._checks_contexto_cabecalho[campo].get()) == 1
        ]

    def _normalizar_lista_chaves(self, chaves: list[str]) -> list[str]:
        limpas: list[str] = []
        for bruto in chaves:
            chave = str(bruto or "").strip()
            if chave and chave not in limpas:
                limpas.append(chave)
        return limpas

    def _definir_chaves_cadastradas(self, chaves: list[str], *, atualizar_ui: bool = False) -> None:
        self._chaves_cadastradas = self._normalizar_lista_chaves(chaves)
        if atualizar_ui:
            self._reconstruir_linhas_chaves()
            self._atualizar_resumo_chaves()

    def _listar_chaves_digitadas(self) -> list[str]:
        return list(self._chaves_cadastradas)

    def _reconstruir_linhas_chaves(self) -> None:
        for widget in self._scroll_chaves.winfo_children():
            widget.destroy()
        if not self._chaves_cadastradas:
            ctk.CTkLabel(
                self._scroll_chaves,
                text="Nenhuma chave ainda. Cole uma nova chave acima ou importe do arquivo local.",
                font=FONT_DICA_ABA,
                text_color=COR_TEXTO_SECUNDARIO,
                justify="left",
                wraplength=700,
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", pady=4)
            return
        for indice, chave in enumerate(self._chaves_cadastradas):
            linha = ctk.CTkFrame(self._scroll_chaves, fg_color="transparent")
            linha.grid(row=indice, column=0, sticky="ew", pady=3)
            linha.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                linha,
                text=f"{indice + 1}.",
                width=28,
                font=FONT_INTERFACE,
                anchor="e",
            ).grid(row=0, column=0, sticky="w", padx=(0, 6))
            lbl_chave = ctk.CTkLabel(
                linha,
                text=chave,
                font=FONT_DICA_ABA,
                anchor="w",
                justify="left",
                wraplength=620,
            )
            lbl_chave.grid(row=0, column=1, sticky="ew")
            ctk.CTkButton(
                linha,
                text="Remover",
                width=92,
                height=28,
                font=FONT_DICA_ABA,
                fg_color="transparent",
                border_width=1,
                border_color=resolver_cor(COR_ERRO),
                text_color=resolver_cor(COR_ERRO),
                hover_color=resolver_cor(COR_FUNDO_SECUNDARIO),
                command=lambda idx=indice: self._remover_chave_ui(idx),
            ).grid(row=0, column=2, sticky="ne", padx=(8, 0))

    def _adicionar_chave_ui(self) -> None:
        chave = self.entry_nova_chave.get().strip()
        if not chave:
            messagebox.showwarning(
                "Chave vazia",
                "Cole ou digite a chave da API antes de adicionar.",
                parent=self,
            )
            return
        if chave in self._chaves_cadastradas:
            messagebox.showinfo(
                "Chave já cadastrada",
                "Esta chave já está na lista.",
                parent=self,
            )
            self.entry_nova_chave.delete(0, "end")
            return
        self._chaves_cadastradas.append(chave)
        self.entry_nova_chave.delete(0, "end")
        reiniciar_historico_desfazer_widget(self.entry_nova_chave)
        self._reconstruir_linhas_chaves()
        self._atualizar_resumo_chaves()
        self._atualizar_combo_chave_ativa()

    def _remover_chave_ui(self, indice: int) -> None:
        if indice < 0 or indice >= len(self._chaves_cadastradas):
            return
        rotulo = self._chaves_cadastradas[indice]
        if not messagebox.askyesno(
            "Remover chave",
            f"Remover esta chave da lista?\n\n{rotulo}\n\nEla só será apagada do .env ao clicar em Salvar.",
            parent=self,
        ):
            return
        self._chaves_cadastradas.pop(indice)
        self._reconstruir_linhas_chaves()
        self._atualizar_resumo_chaves()
        self._atualizar_combo_chave_ativa()

    def _importar_arquivo_local(self) -> None:
        importadas = self._normalizar_lista_chaves(listar_chaves_gemini())
        if not importadas:
            messagebox.showinfo(
                "Importar chaves",
                f"Nenhuma chave encontrada no .env ou em «{nome_arquivo_importacao_chaves()}».",
                parent=self,
            )
            return
        merged = self._chaves_cadastradas[:]
        novas = 0
        for chave in importadas:
            if chave not in merged:
                merged.append(chave)
                novas += 1
        self._definir_chaves_cadastradas(merged, atualizar_ui=True)
        self._atualizar_combo_chave_ativa()
        if novas:
            messagebox.showinfo(
                "Importar chaves",
                f"{novas} chave(s) adicionada(s) à lista.",
                parent=self,
            )
        else:
            messagebox.showinfo(
                "Importar chaves",
                "Todas as chaves do arquivo local já estavam na lista.",
                parent=self,
            )

    def _atualizar_resumo_chaves(self) -> None:
        chaves = self._listar_chaves_digitadas()
        if not chaves:
            self.lbl_resumo_chaves.configure(
                text="Nenhuma chave cadastrada — a reescrita com IA ficará indisponível até você salvar ao menos uma."
            )
            return
        if len(chaves) == 1:
            self.lbl_resumo_chaves.configure(
                text=f"1 chave cadastrada:\n{chaves[0]}"
            )
            return
        self.lbl_resumo_chaves.configure(
            text=f"{len(chaves)} chaves cadastradas — prontas para uso e rodízio entre reescritas."
        )

    def _rotulo_modo(self, valor: str | None) -> str:
        modo = str(valor or MODO_ROTACAO_FIXO).strip().lower()
        for rotulo, interno in self._MAPA_ROTACAO.items():
            if interno == modo:
                return rotulo
        return next(iter(self._MAPA_ROTACAO))

    def _modo_selecionado(self) -> str:
        return self._MAPA_ROTACAO.get(self.combo_modo_rotacao.get(), MODO_ROTACAO_FIXO)

    def _atualizar_combo_chave_ativa(self) -> None:
        chaves = self._listar_chaves_digitadas()
        rotulos = (
            [f"{indice + 1}. {chave}" for indice, chave in enumerate(chaves)]
            if chaves
            else ["Sem chaves"]
        )
        self._mapa_rotulos_chaves = {rotulo: idx for idx, rotulo in enumerate(rotulos)}
        self.combo_chave_ativa.configure(values=rotulos)
        if chaves:
            indice = int(self._config.get("indice_chave_ativa") or 0) % len(chaves)
            self.combo_chave_ativa.set(rotulos[indice])
            self.combo_chave_ativa.configure(
                state="readonly" if self._modo_selecionado() == MODO_ROTACAO_FIXO else "disabled"
            )
        else:
            self.combo_chave_ativa.set("Sem chaves")
            self.combo_chave_ativa.configure(state="disabled")

    def _primeira_chave_ui(self) -> str:
        chaves = self._listar_chaves_digitadas()
        if not chaves:
            return ""
        if self._modo_selecionado() == MODO_ROTACAO_FIXO:
            rotulo = self.combo_chave_ativa.get().strip()
            indice = self._mapa_rotulos_chaves.get(rotulo)
            if indice is not None and 0 <= indice < len(chaves):
                return chaves[indice]
        return chaves[0]

    def _aplicar_lista_modelos(
        self,
        modelos: list[str],
        *,
        modelo_preferido: str | None = None,
    ) -> None:
        preferido = (modelo_preferido or self.combo_modelo.get() or "").strip()
        base = [m for m in modelos if str(m).strip()]
        if not base:
            base = list(MODELOS_GEMINI_SUGERIDOS)
        if preferido and preferido not in base:
            base = [preferido] + base
        self._modelos_disponiveis = base
        self.combo_modelo.configure(values=base)
        if preferido and preferido in base:
            self.combo_modelo.set(preferido)
        else:
            self.combo_modelo.set(base[0])

    def _janela_viva(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    def _atualizar_modelos_api(self, *, silencioso: bool = False) -> None:
        if self._atualizando_modelos:
            return
        chave = self._primeira_chave_ui()
        if not chave:
            if not silencioso:
                messagebox.showwarning(
                    "Chave necessária",
                    "Informe ao menos uma chave Gemini para buscar os modelos na API.",
                    parent=self,
                )
            self.lbl_modelo_info.configure(
                text="Informe uma chave para preencher a lista pela API. Enquanto isso, usamos a lista local."
            )
            return

        self._atualizando_modelos = True
        self.btn_atualizar_modelos.configure(state="disabled", text="Atualizando…")
        self.lbl_modelo_info.configure(text="Consultando modelos disponíveis na API…")

        def trabalhador() -> None:
            lista, erro = listar_modelos_gemini(chave)

            def concluir() -> None:
                self._fim_atualizar_modelos(lista, erro, silencioso)

            try:
                if self._janela_viva():
                    self.after(0, concluir)
            except Exception:
                pass

        threading.Thread(target=trabalhador, daemon=True).start()

    def _fim_atualizar_modelos(
        self,
        lista: list[str],
        erro: str | None,
        silencioso: bool,
    ) -> None:
        self._atualizando_modelos = False
        if not self._janela_viva():
            return
        try:
            self.btn_atualizar_modelos.configure(state="normal", text="Atualizar lista")
        except Exception:
            return

        if erro or not lista:
            self.lbl_modelo_info.configure(
                text=erro
                or "Não foi possível obter a lista. Mantidos os modelos locais de fallback."
            )
            if not silencioso:
                messagebox.showwarning(
                    "Lista de modelos",
                    erro
                    or "A API não devolveu modelos. A lista local de fallback foi mantida.",
                    parent=self,
                )
            return

        preferido = self.combo_modelo.get().strip()
        self._aplicar_lista_modelos(lista, modelo_preferido=preferido)
        self.lbl_modelo_info.configure(
            text=f"{len(lista)} modelo(s) disponíveis na API para esta chave."
        )
        if not silencioso:
            messagebox.showinfo(
                "Lista de modelos",
                f"Lista atualizada com {len(lista)} modelo(s) retornados pela API.",
                parent=self,
            )

    def _testar_modelo_selecionado(self) -> None:
        if self._testando_modelo:
            return
        chave = self._primeira_chave_ui()
        modelo = self.combo_modelo.get().strip()
        if not chave:
            messagebox.showwarning(
                "Testar modelo",
                "Informe ao menos uma chave Gemini antes de testar.",
                parent=self,
            )
            return
        if not modelo:
            messagebox.showwarning(
                "Testar modelo",
                "Selecione um modelo Gemini para testar.",
                parent=self,
            )
            return

        self._testando_modelo = True
        self.btn_testar_modelo.configure(state="disabled", text="Testando…")
        self.lbl_modelo_info.configure(text=f"Testando «{modelo}» na API…")

        def trabalhador() -> None:
            ok, mensagem = testar_modelo_gemini(chave, modelo)

            def concluir() -> None:
                self._fim_testar_modelo(ok, mensagem)

            try:
                if self._janela_viva():
                    self.after(0, concluir)
            except Exception:
                pass

        threading.Thread(target=trabalhador, daemon=True).start()

    def _fim_testar_modelo(self, ok: bool, mensagem: str) -> None:
        self._testando_modelo = False
        if not self._janela_viva():
            return
        try:
            self.btn_testar_modelo.configure(state="normal", text="Testar modelo")
        except Exception:
            return
        resumo = mensagem.splitlines()[0] if mensagem else ("OK" if ok else "Falha")
        self.lbl_modelo_info.configure(text=resumo)
        if ok:
            messagebox.showinfo("Testar modelo", mensagem, parent=self)
        else:
            messagebox.showerror("Testar modelo", mensagem, parent=self)

    def _nomes_prompts(self) -> list[str]:
        nomes = [str(prompt.get("nome") or "Prompt sem nome").strip() or "Prompt sem nome" for prompt in self._prompts]
        return nomes or ["Prompt sem nome"]

    def _indice_prompt_atual(self) -> int:
        for indice, prompt in enumerate(self._prompts):
            if str(prompt.get("id") or "") == self._prompt_atual_id:
                return indice
        return 0

    def _salvar_editor_no_prompt_atual(self) -> None:
        if not self._prompts:
            return
        indice = self._indice_prompt_atual()
        self._prompts[indice]["nome"] = (
            self.entry_nome_prompt.get().strip() or "Prompt sem nome"
        )
        self._prompts[indice]["texto"] = self.txt_prompt.get("1.0", "end").strip()

    def _carregar_prompt_no_editor(self, prompt_id: str) -> None:
        if not self._prompts:
            self._prompts = [{"id": uuid4().hex, "nome": "Prompt sem nome", "texto": ""}]
        for indice, prompt in enumerate(self._prompts):
            if str(prompt.get("id") or "") == prompt_id:
                self._prompt_atual_id = prompt_id
                self.combo_prompts.configure(values=self._nomes_prompts())
                self.combo_prompts.set(self._nomes_prompts()[indice])
                self.entry_nome_prompt.delete(0, "end")
                self.entry_nome_prompt.insert(0, str(prompt.get("nome") or ""))
                self.txt_prompt.delete("1.0", "end")
                self.txt_prompt.insert("1.0", str(prompt.get("texto") or ""))
                reiniciar_historico_desfazer_widget(self.txt_prompt)
                if hasattr(self.master, "_agendar_verificacao_ortografia"):
                    self.master._agendar_verificacao_ortografia(self.txt_prompt)
                return
        self._carregar_prompt_no_editor(str(self._prompts[0].get("id") or ""))

    def _ao_trocar_prompt(self, nome_selecionado: str) -> None:
        self._salvar_editor_no_prompt_atual()
        for prompt in self._prompts:
            if str(prompt.get("nome") or "Prompt sem nome") == nome_selecionado:
                self._carregar_prompt_no_editor(str(prompt.get("id") or ""))
                return

    def _novo_prompt(self) -> None:
        self._salvar_editor_no_prompt_atual()
        prompt = {
            "id": uuid4().hex,
            "nome": f"Novo prompt {len(self._prompts) + 1}",
            "texto": "",
        }
        self._prompts.append(prompt)
        self._carregar_prompt_no_editor(prompt["id"])

    def _duplicar_prompt(self) -> None:
        self._salvar_editor_no_prompt_atual()
        atual = self._prompts[self._indice_prompt_atual()]
        copia = {
            "id": uuid4().hex,
            "nome": f"{str(atual.get('nome') or 'Prompt').strip()} (cópia)",
            "texto": str(atual.get("texto") or ""),
        }
        self._prompts.append(copia)
        self._carregar_prompt_no_editor(copia["id"])

    def _excluir_prompt(self) -> None:
        if len(self._prompts) <= 1:
            messagebox.showwarning(
                "Prompts",
                "Mantenha ao menos um prompt cadastrado.",
                parent=self,
            )
            return
        indice = self._indice_prompt_atual()
        nome = str(self._prompts[indice].get("nome") or "Prompt")
        if not messagebox.askyesno(
            "Excluir prompt",
            f"Excluir o prompt '{nome}'?",
            parent=self,
        ):
            return
        self._prompts.pop(indice)
        self._carregar_prompt_no_editor(str(self._prompts[max(0, indice - 1)].get("id") or ""))

    def _coletar_indice_chave_ativa(self, total_chaves: int) -> int:
        if total_chaves <= 0:
            return 0
        rotulo = self.combo_chave_ativa.get().strip()
        indice = self._mapa_rotulos_chaves.get(rotulo, 0)
        return max(0, min(indice, total_chaves - 1))

    def _salvar(self) -> None:
        self._salvar_editor_no_prompt_atual()

        prompts_limpios = []
        for item in self._prompts:
            texto = str(item.get("texto") or "").strip()
            nome = str(item.get("nome") or "Prompt sem nome").strip() or "Prompt sem nome"
            if texto:
                prompts_limpios.append(
                    {
                        "id": str(item.get("id") or uuid4().hex),
                        "nome": nome,
                        "texto": texto,
                    }
                )
        if not prompts_limpios:
            messagebox.showwarning(
                "Prompts",
                "Preencha ao menos um prompt com texto.",
                parent=self,
            )
            return
        if self._prompt_atual_id not in {item["id"] for item in prompts_limpios}:
            self._prompt_atual_id = prompts_limpios[0]["id"]

        try:
            dias_historico = max(0, int(self.entry_dias_historico.get().strip() or "0"))
        except ValueError:
            messagebox.showwarning(
                "Histórico",
                "Informe um número inteiro de dias de histórico.",
                parent=self,
            )
            return

        try:
            minimo_caracteres = max(
                0, int(self.entry_min_caracteres_historico.get().strip() or "0")
            )
        except ValueError:
            messagebox.showwarning(
                "Histórico",
                "Informe um número inteiro de caracteres mínimos para o histórico.",
                parent=self,
            )
            return

        modelo = self.combo_modelo.get().strip()
        if not modelo:
            messagebox.showwarning(
                "Modelo",
                "Informe o modelo Gemini.",
                parent=self,
            )
            return

        chaves = salvar_chaves_gemini(self._listar_chaves_digitadas())
        config_salva = salvar_config_ia(
            {
                "modelo": modelo,
                "modo_rotacao": self._modo_selecionado(),
                "indice_chave_ativa": self._coletar_indice_chave_ativa(len(chaves)),
                "dias_historico": dias_historico,
                "minimo_caracteres_historico": minimo_caracteres,
                "remover_primeiro_paragrafo": bool(self.chk_primeiro.get() == 1),
                "remover_ultimo_paragrafo": bool(self.chk_ultimo.get() == 1),
                "campos_contexto_cabecalho": self._campos_contexto_cabecalho_selecionados(),
                "prompt_selecionado_id": self._prompt_atual_id,
                "prompts": prompts_limpios,
            }
        )
        self._config = config_salva
        if callable(self._ao_salvar_callback):
            try:
                self._ao_salvar_callback()
            except Exception:
                pass
        self.destroy()
