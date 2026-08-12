"""Formulário do relatório diário: textos, horários e persistência no JSON."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from rdo_diario.calculo_metricas_horas import calcular_metricas_horas_para_dia
from rdo_diario.gui.tema import (
    COR_TEXTO_SECUNDARIO,
    FONT_CONTAGEM_MES,
    FONT_DATA_SELECIONADA,
    FONT_GRUPO,
    FONT_INTERFACE,
    aplicar_validacao_entrada_ctk,
    criar_painel_ctk_com_titulo,
    icursor_fim_entrada_ctk,
    obter_cores_tema,
    opcoes_caixa_texto_ctk,
    opcoes_campo_entrada_ctk,
    resolver_entrada_ctk,
    texto_interno_campo,
)
from rdo_diario.horario_util import (
    normalizar_duracao_hhmm,
    normalizar_texto_horario,
)
from rdo_diario.schema import (
    CAMPOS_JSON_DESLOCAMENTO,
    CAMPOS_JSON_HORARIOS,
    CAMPOS_JSON_PONTO,
    CHAVE_JSON_BATIDAS_PONTO,
    CHAVE_JSON_FOLHA_RELATORIO_MES,
    CHAVE_JSON_INCLUIR_DESLOCAMENTO_FT,
    CHAVE_JSON_METRICAS_HORAS,
    CHAVE_JSON_NUMERO_RELATORIO_MES,
    ROTULOS_HORARIO,
    ROTULOS_TEMPO_ATIVIDADE_DIA,
    ROTULOS_TEXTO_DIA,
    aplicar_metadados_data_no_registro_diario,
    atualizar_numero_folha_mes_em_registros,
    extrair_horarios_do_registro_dia,
    incluir_deslocamento_nas_horas,
    nome_dia_semana_portugues,
    registro_de_dia_possui_conteudo,
)

if TYPE_CHECKING:
    from rdo_diario.gui.app import AplicacaoRdo

# Extra-escopo / ociosidade: compactos por omissão; expandem ao receber foco.
# Registo de serviço: cresce com a janela e cede espaço quando o rodapé expande.
_ALTURA_TEXTO_SERVICO = 56
_ALTURA_TEXTO_RODAPE = 48
_ALTURA_TEXTO_RODAPE_EXPANDIDO = 160
_LARGURA_CAMPO_ENTRADA = 60
_CAMPOS_TEXTO_EXPANDIVEIS = ("registro_extra_escopo", "registro_ociosidade")
_MAPA_TEMPO_PARA_CAMPO_TEXTO = {
    "tempo_extra_escopo": "registro_extra_escopo",
    "tempo_ociosidade": "registro_ociosidade",
}


class MixinFormularioDia:
    """Campos de texto, horários e leitura/gravação do registro do dia."""

    _widgets_campos_dia: dict[str, ctk.CTkTextbox]
    _widgets_tempo_atividade: dict[str, ctk.CTkEntry]
    _widgets_horarios: dict[str, ctk.CTkEntry]
    _recipientes_texto_dia: dict[str, ctk.CTkFrame]
    _linhas_grid_campo_texto: dict[str, int]
    _grid_campos_relatorio: ctk.CTkFrame | None
    _campo_texto_expandido: str | None
    _id_agendar_recolher_texto: str | None
    _widget_incluir_deslocamento_ft: ctk.CTkCheckBox | None
    _rotulo_texto_data: ctk.CTkLabel | None
    _rotulo_contagem_mes: ctk.CTkLabel | None
    _comando_validacao_entrada_hora: Any
    _comando_validacao_entrada_duracao: Any
    _data_em_edicao: date
    _documento_atual: dict[str, Any] | None
    _config_regras_horas: dict[str, Any]
    _id_agendamento_salvar: str | None
    TAG_ERRO_ORTOGRAFIA: str

    def _criar_grupo_ctk(
        self,
        pai: ctk.CTkBaseClass,
        titulo: str,
        *,
        compacto: bool = False,
    ) -> tuple[ctk.CTkFrame, ctk.CTkFrame, ctk.CTkFrame]:
        return criar_painel_ctk_com_titulo(pai, titulo, compacto=compacto)

    def _ligar_ortografia_caixa(self, texto: ctk.CTkTextbox) -> None:
        interno = texto_interno_campo(texto)
        interno.tag_configure(
            self.TAG_ERRO_ORTOGRAFIA,
            foreground=obter_cores_tema()["erro"],
            underline=True,
        )
        interno.bind(
            "<KeyRelease>",
            lambda e, w=texto: self._ao_tecla_released_campo_relatorio(w, e),
        )
        interno.bind("<Button-3>", lambda e, w=texto: self._menu_correcoes_ortografia(w, e))
        interno.bind(
            "<Control-Button-1>",
            lambda e, w=texto: self._menu_correcoes_ortografia(w, e),
        )

    def _criar_texto_multilinha(
        self,
        pai: ctk.CTkBaseClass,
        *,
        altura_px: int = _ALTURA_TEXTO_SERVICO,
        expandir_verticalmente: bool = True,
        campo: str | None = None,
    ) -> ctk.CTkTextbox:
        """Cria caixa de texto. Se expandir, acompanha o pai e não desce de ``altura_px``."""
        recipiente = ctk.CTkFrame(pai, fg_color="transparent", height=altura_px)
        if expandir_verticalmente:
            recipiente.pack(fill="both", expand=True, pady=(1, 0))
        else:
            recipiente.pack(fill="x", expand=False, pady=(1, 0))
        recipiente.pack_propagate(False)
        texto = ctk.CTkTextbox(recipiente, **opcoes_caixa_texto_ctk(altura_px=altura_px))
        texto.pack(fill="both", expand=True)

        def _sincronizar_altura(_evento: tk.Event | None = None) -> None:
            try:
                disponivel = int(recipiente.winfo_height())
            except tk.TclError:
                return
            if disponivel < 2:
                return
            expandido = campo is not None and campo == getattr(self, "_campo_texto_expandido", None)
            if expandir_verticalmente or expandido:
                alvo = max(altura_px, disponivel)
            else:
                alvo = altura_px
            if int(texto.cget("height")) != alvo:
                texto.configure(height=alvo)

        recipiente.bind("<Configure>", lambda _e: _sincronizar_altura())
        if campo is not None:
            self._recipientes_texto_dia[campo] = recipiente
        self._ligar_ortografia_caixa(texto)
        return texto

    def _montar_linha_tempo_atividade(
        self,
        pai: ctk.CTkBaseClass,
        chave_json_tempo: str,
    ) -> None:
        rotulo = ROTULOS_TEMPO_ATIVIDADE_DIA[chave_json_tempo]
        ctk.CTkLabel(pai, text=rotulo + ":", anchor="w", font=FONT_INTERFACE).pack(
            side="left", padx=(0, 6)
        )
        entrada = ctk.CTkEntry(pai, **opcoes_campo_entrada_ctk(largura=_LARGURA_CAMPO_ENTRADA))
        entrada.pack(side="left")
        aplicar_validacao_entrada_ctk(entrada, self._comando_validacao_entrada_duracao)
        entrada.bind("<KeyRelease>", self._ao_tecla_solta_campo_duracao)
        entrada.bind("<FocusOut>", lambda _e, w=entrada: self._ao_sair_foco_campo_duracao(w))
        campo_texto = _MAPA_TEMPO_PARA_CAMPO_TEXTO.get(chave_json_tempo)
        if campo_texto is not None:
            entrada.bind(
                "<FocusIn>",
                lambda _e, c=campo_texto: self._ao_foco_campo_texto_expansivel(c),
            )
            entrada.bind(
                "<FocusOut>",
                lambda _e, c=campo_texto: self._ao_sair_foco_campo_texto_expansivel(c),
                add="+",
            )
        self._widgets_tempo_atividade[chave_json_tempo] = entrada

    def _chave_tempo_do_campo_texto(self, campo: str) -> str | None:
        if campo == "registro_extra_escopo":
            return "tempo_extra_escopo"
        if campo == "registro_ociosidade":
            return "tempo_ociosidade"
        return None

    def _ligar_foco_expansao_caixa(self, texto: ctk.CTkTextbox, campo: str) -> None:
        interno = texto_interno_campo(texto)
        interno.bind(
            "<FocusIn>",
            lambda _e, c=campo: self._ao_foco_campo_texto_expansivel(c),
            add="+",
        )
        interno.bind(
            "<FocusOut>",
            lambda _e, c=campo: self._ao_sair_foco_campo_texto_expansivel(c),
            add="+",
        )

    def _widget_pertence_ao_campo_texto(self, widget: tk.Misc | None, campo: str) -> bool:
        if widget is None:
            return False
        texto = self._widgets_campos_dia.get(campo)
        if texto is not None:
            if widget is texto or widget is texto_interno_campo(texto):
                return True
        chave_tempo = self._chave_tempo_do_campo_texto(campo)
        if chave_tempo is None:
            return False
        entrada = self._widgets_tempo_atividade.get(chave_tempo)
        if entrada is None:
            return False
        return widget is entrada or widget is getattr(entrada, "_entry", None)

    def _expandir_campo_texto_rodape(self, campo: str) -> None:
        if campo not in _CAMPOS_TEXTO_EXPANDIVEIS:
            return
        if self._campo_texto_expandido == campo:
            return
        if self._campo_texto_expandido is not None:
            self._recolher_campo_texto_rodape(animar=False)
        grid = self._grid_campos_relatorio
        if grid is None:
            return
        linha = self._linhas_grid_campo_texto.get(campo)
        if linha is None:
            return
        self._campo_texto_expandido = campo
        grid.grid_rowconfigure(0, weight=0, minsize=_ALTURA_TEXTO_SERVICO + 24)
        grid.grid_rowconfigure(linha, weight=1, minsize=_ALTURA_TEXTO_RODAPE_EXPANDIDO)
        recipiente = self._recipientes_texto_dia.get(campo)
        if recipiente is not None:
            recipiente.pack_configure(fill="both", expand=True)
            recipiente.configure(height=_ALTURA_TEXTO_RODAPE_EXPANDIDO)
        texto = self._widgets_campos_dia.get(campo)
        if texto is not None:
            texto.configure(height=_ALTURA_TEXTO_RODAPE_EXPANDIDO)

    def _recolher_campo_texto_rodape(self, *, animar: bool = True) -> None:
        del animar  # reservado; recolha é imediata
        campo = self._campo_texto_expandido
        if campo is None:
            return
        grid = self._grid_campos_relatorio
        linha = self._linhas_grid_campo_texto.get(campo)
        self._campo_texto_expandido = None
        if grid is not None and linha is not None:
            grid.grid_rowconfigure(linha, weight=0, minsize=0)
            grid.grid_rowconfigure(0, weight=1, minsize=_ALTURA_TEXTO_SERVICO + 24)
        recipiente = self._recipientes_texto_dia.get(campo)
        if recipiente is not None:
            recipiente.pack_configure(fill="x", expand=False)
            recipiente.configure(height=_ALTURA_TEXTO_RODAPE)
        texto = self._widgets_campos_dia.get(campo)
        if texto is not None:
            texto.configure(height=_ALTURA_TEXTO_RODAPE)

    def _ao_foco_campo_texto_expansivel(self, campo: str) -> None:
        if self._id_agendar_recolher_texto is not None:
            self.after_cancel(self._id_agendar_recolher_texto)
            self._id_agendar_recolher_texto = None
        if campo == "registro_servico":
            self._recolher_campo_texto_rodape()
            return
        self._expandir_campo_texto_rodape(campo)

    def _ao_sair_foco_campo_texto_expansivel(self, campo: str) -> None:
        if self._campo_texto_expandido != campo:
            return
        if self._id_agendar_recolher_texto is not None:
            self.after_cancel(self._id_agendar_recolher_texto)
        self._id_agendar_recolher_texto = self.after(120, self._verificar_recolher_texto_rodape)

    def _verificar_recolher_texto_rodape(self) -> None:
        self._id_agendar_recolher_texto = None
        campo = self._campo_texto_expandido
        if campo is None:
            return
        try:
            foco = self.focus_get()
        except tk.TclError:
            foco = None
        if self._widget_pertence_ao_campo_texto(foco, campo):
            return
        # Troca directa entre extra-escopo e ociosidade: expandir o novo sem colapsar.
        for outro in _CAMPOS_TEXTO_EXPANDIVEIS:
            if outro != campo and self._widget_pertence_ao_campo_texto(foco, outro):
                self._expandir_campo_texto_rodape(outro)
                return
        self._recolher_campo_texto_rodape()

    def _montar_campo_texto_dia_fixo(
        self,
        pai: ctk.CTkBaseClass,
        campo: str,
        *,
        altura_px: int,
        expandir_verticalmente: bool,
        pady_rotulo: tuple[int, int] = (4, 0),
    ) -> None:
        chave_tempo = self._chave_tempo_do_campo_texto(campo)
        linha_rotulo = ctk.CTkFrame(pai, fg_color="transparent")
        linha_rotulo.pack(fill="x", pady=pady_rotulo)
        ctk.CTkLabel(
            linha_rotulo,
            text=ROTULOS_TEXTO_DIA[campo] + ":",
            anchor="w",
            font=FONT_INTERFACE,
        ).pack(side="left")
        if chave_tempo is not None:
            # Título à esquerda; tempo da atividade à direita, na mesma linha.
            bloco_tempo = ctk.CTkFrame(linha_rotulo, fg_color="transparent")
            bloco_tempo.pack(side="right")
            self._montar_linha_tempo_atividade(bloco_tempo, chave_tempo)

        texto = self._criar_texto_multilinha(
            pai,
            altura_px=altura_px,
            expandir_verticalmente=expandir_verticalmente,
            campo=campo,
        )
        self._widgets_campos_dia[campo] = texto
        if campo in _CAMPOS_TEXTO_EXPANDIVEIS or campo == "registro_servico":
            self._ligar_foco_expansao_caixa(texto, campo)

    def _montar_coluna_formulario_dia(self, coluna_formulario: ctk.CTkBaseClass) -> None:
        grupo_dia, cabecalho, moldura_dia = self._criar_grupo_ctk(
            coluna_formulario, "Relatório", compacto=True
        )
        grupo_dia.pack(fill="both", expand=True)

        # Título + data + contagem do mês na mesma linha do cabeçalho.
        ctk.CTkLabel(
            cabecalho,
            text="Data selecionada:",
            anchor="w",
            font=FONT_INTERFACE,
        ).pack(side="left", padx=(16, 0))
        self._rotulo_texto_data = ctk.CTkLabel(
            cabecalho,
            text="",
            font=FONT_DATA_SELECIONADA,
            anchor="w",
        )
        self._rotulo_texto_data.pack(side="left", padx=(6, 0))
        self._rotulo_contagem_mes = ctk.CTkLabel(
            cabecalho,
            text="",
            font=FONT_CONTAGEM_MES,
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self._rotulo_contagem_mes.pack(side="left", padx=(12, 0))

        # Linhas: serviço | extra-escopo | ociosidade | horários.
        # Extra/ociosidade expandem ao foco e o serviço cede espaço.
        campos = ctk.CTkFrame(moldura_dia, fg_color="transparent")
        campos.pack(fill="both", expand=True)
        self._grid_campos_relatorio = campos
        self._linhas_grid_campo_texto = {
            "registro_servico": 0,
            "registro_extra_escopo": 1,
            "registro_ociosidade": 2,
        }
        campos.grid_columnconfigure(0, weight=1)
        campos.grid_rowconfigure(0, weight=1, minsize=_ALTURA_TEXTO_SERVICO + 24)
        campos.grid_rowconfigure(1, weight=0)
        campos.grid_rowconfigure(2, weight=0)
        campos.grid_rowconfigure(3, weight=0)

        area_servico = ctk.CTkFrame(campos, fg_color="transparent")
        area_servico.grid(row=0, column=0, sticky="nsew")
        self._montar_campo_texto_dia_fixo(
            area_servico,
            "registro_servico",
            altura_px=_ALTURA_TEXTO_SERVICO,
            expandir_verticalmente=True,
            pady_rotulo=(0, 0),
        )

        area_extra = ctk.CTkFrame(campos, fg_color="transparent")
        area_extra.grid(row=1, column=0, sticky="nsew")
        self._montar_campo_texto_dia_fixo(
            area_extra,
            "registro_extra_escopo",
            altura_px=_ALTURA_TEXTO_RODAPE,
            expandir_verticalmente=False,
            pady_rotulo=(4, 0),
        )

        area_ocio = ctk.CTkFrame(campos, fg_color="transparent")
        area_ocio.grid(row=2, column=0, sticky="nsew")
        self._montar_campo_texto_dia_fixo(
            area_ocio,
            "registro_ociosidade",
            altura_px=_ALTURA_TEXTO_RODAPE,
            expandir_verticalmente=False,
            pady_rotulo=(4, 0),
        )

        area_horarios = ctk.CTkFrame(campos, fg_color="transparent")
        area_horarios.grid(row=3, column=0, sticky="ew")
        self._montar_secao_horarios(area_horarios)

    def _montar_secao_horarios(self, pai: ctk.CTkBaseClass) -> None:
        # Sem painel aninhado: só rótulo + campos, para não gastar altura em bordas/padding.
        ctk.CTkLabel(
            pai,
            text="Horários — ponto e deslocamento (24h, HH:MM)",
            font=FONT_GRUPO,
            anchor="w",
        ).pack(anchor="w", fill="x", pady=(4, 1))

        def par_horario(linha: ctk.CTkFrame, chave_campo: str, *, espacamento_direita: int = 16) -> None:
            bloco = ctk.CTkFrame(linha, fg_color="transparent")
            bloco.pack(side="left", padx=(0, espacamento_direita), pady=0)
            ctk.CTkLabel(bloco, text=ROTULOS_HORARIO[chave_campo] + ":", anchor="w", font=FONT_INTERFACE).pack(
                side="left", padx=(0, 4)
            )
            ent = ctk.CTkEntry(bloco, **opcoes_campo_entrada_ctk(largura=_LARGURA_CAMPO_ENTRADA))
            ent.pack(side="left")
            aplicar_validacao_entrada_ctk(ent, self._comando_validacao_entrada_hora)
            ent.bind("<KeyRelease>", self._ao_tecla_solta_campo_hora)
            ent.bind("<FocusOut>", lambda _e, w=ent: self._ao_sair_foco_campo_hora(w))
            self._configurar_enter_proximo_campo_horario(ent, chave_campo)
            self._widgets_horarios[chave_campo] = ent

        linha_ponto = ctk.CTkFrame(pai, fg_color="transparent")
        linha_ponto.pack(fill="x")
        ctk.CTkLabel(linha_ponto, text="Ponto:", font=FONT_GRUPO, anchor="w").pack(
            side="left", padx=(0, 6)
        )
        for chave in CAMPOS_JSON_PONTO:
            par_horario(linha_ponto, chave, espacamento_direita=8)

        linha_desloc = ctk.CTkFrame(pai, fg_color="transparent")
        linha_desloc.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(
            linha_desloc,
            text="Deslocamento:",
            font=FONT_GRUPO,
            anchor="w",
        ).pack(side="left", padx=(0, 10))
        for chave in CAMPOS_JSON_DESLOCAMENTO:
            par_horario(linha_desloc, chave)
        self._widget_incluir_deslocamento_ft = ctk.CTkCheckBox(
            linha_desloc,
            text="Incluir Deslocamento",
            font=FONT_INTERFACE,
            command=self._ao_alterar_incluir_deslocamento_ft,
        )
        self._widget_incluir_deslocamento_ft.pack(side="left", padx=(8, 0))

    def _ao_alterar_incluir_deslocamento_ft(self) -> None:
        self._atualizar_rotulo_jornada_liquida()
        self._agendar_salvamento_automatico()

    def _aplicar_formatacao_campo_entrada(self, entrada: ctk.CTkEntry, tipo: str = "horario") -> None:
        texto = entrada.get()
        if ":" in texto:
            return
        digitos = "".join(c for c in texto if c.isdigit())
        if len(digitos) == 4:
            normalizador = normalizar_texto_horario if tipo == "horario" else normalizar_duracao_hhmm
            normalizado = normalizador(digitos)
            if normalizado:
                entrada.delete(0, "end")
                entrada.insert(0, normalizado)
                icursor_fim_entrada_ctk(entrada)

    def _normalizar_campo_entrada(self, entrada: ctk.CTkEntry, tipo: str = "horario") -> None:
        bruto = entrada.get().strip()
        if not bruto:
            return
        normalizador = normalizar_texto_horario if tipo == "horario" else normalizar_duracao_hhmm
        normalizado = normalizador(bruto)
        if normalizado != bruto or (bruto and not normalizado):
            entrada.delete(0, "end")
            if normalizado:
                entrada.insert(0, normalizado)

    def _configurar_enter_proximo_campo_horario(self, entrada: ctk.CTkEntry, chave_campo: str) -> None:
        def ao_enter(_evento: tk.Event) -> str:
            self._normalizar_campo_entrada(entrada, "horario")
            self._atualizar_rotulo_jornada_liquida()
            self._agendar_salvamento_automatico()
            try:
                indice = CAMPOS_JSON_HORARIOS.index(chave_campo)
            except ValueError:
                return "break"
            if indice + 1 < len(CAMPOS_JSON_HORARIOS):
                proximo = self._widgets_horarios.get(CAMPOS_JSON_HORARIOS[indice + 1])
                if proximo is not None:
                    proximo.focus_set()
            return "break"

        entrada.bind("<Return>", ao_enter)
        entrada.bind("<KP_Enter>", ao_enter)

    def _ao_tecla_solta_campo_hora(self, evento: tk.Event) -> None:
        entrada = resolver_entrada_ctk(evento.widget, self._widgets_horarios)
        if entrada is not None:
            self.after_idle(lambda e=entrada: self._aplicar_formatacao_campo_entrada(e, "horario"))
        self._atualizar_rotulo_jornada_liquida()
        self._agendar_salvamento_automatico()

    def _ao_sair_foco_campo_hora(self, entrada: ctk.CTkEntry) -> None:
        self._normalizar_campo_entrada(entrada, "horario")
        self._atualizar_rotulo_jornada_liquida()
        self._agendar_salvamento_automatico()

    def _ao_tecla_solta_campo_duracao(self, evento: tk.Event) -> None:
        entrada = resolver_entrada_ctk(evento.widget, self._widgets_tempo_atividade)
        if entrada is not None:
            self.after_idle(lambda e=entrada: self._aplicar_formatacao_campo_entrada(e, "duracao"))
        self._agendar_salvamento_automatico()

    def _ao_sair_foco_campo_duracao(self, entrada: ctk.CTkEntry) -> None:
        self._normalizar_campo_entrada(entrada, "duracao")
        self._agendar_salvamento_automatico()

    def _atualizar_rotulo_jornada_liquida(self) -> None:
        self._atualizar_painel_metricas_horas()

    def _payload_formulario_dia_sem_contagem_mes(self) -> dict[str, Any]:
        saida: dict[str, Any] = {}
        for chave, widget in self._widgets_campos_dia.items():
            saida[chave] = widget.get("1.0", "end").strip()
        for chave, widget in self._widgets_tempo_atividade.items():
            bruto = widget.get().strip()
            saida[chave] = normalizar_duracao_hhmm(bruto) if bruto else ""
        for chave, widget in self._widgets_horarios.items():
            bruto = widget.get().strip()
            saida[chave] = normalizar_texto_horario(bruto) if bruto else ""
        check = getattr(self, "_widget_incluir_deslocamento_ft", None)
        saida[CHAVE_JSON_INCLUIR_DESLOCAMENTO_FT] = bool(
            check is not None and check.get() == 1
        )
        saida.pop(CHAVE_JSON_BATIDAS_PONTO, None)
        saida.pop("jornada_entrada", None)
        saida.pop("jornada_saida", None)
        return saida

    def _montar_dicionario_dia_desde_formulario(self: AplicacaoRdo) -> dict[str, Any]:
        saida = self._payload_formulario_dia_sem_contagem_mes()
        saida[CHAVE_JSON_METRICAS_HORAS] = calcular_metricas_horas_para_dia(
            self._data_em_edicao, saida, self._config_regras_horas
        )
        posicao, _total, folha = self._calcular_numero_e_folha_mes()
        saida[CHAVE_JSON_NUMERO_RELATORIO_MES] = posicao
        saida[CHAVE_JSON_FOLHA_RELATORIO_MES] = folha
        aplicar_metadados_data_no_registro_diario(self._data_em_edicao.isoformat(), saida)
        return saida

    def _preencher_formulario_com_registro_dia(self, registro: dict[str, Any]) -> None:
        for campo, widget in self._widgets_campos_dia.items():
            valor = str(registro.get(campo, "") or "")
            widget.delete("1.0", "end")
            widget.insert("1.0", valor)
        for campo, widget in self._widgets_tempo_atividade.items():
            widget.delete(0, "end")
            bruto = str(registro.get(campo, "") or "").strip()
            widget.insert(0, normalizar_duracao_hhmm(bruto) if bruto else "")

    def _carregar_registro_dia_no_formulario(self: AplicacaoRdo, dia: date) -> None:
        if not self._documento_atual:
            return
        iso = dia.isoformat()
        registros = self._documento_atual.setdefault("registros_diarios", {})
        registro_bruto = registros.get(iso) if isinstance(registros.get(iso), dict) else {}
        registro = registro_bruto if isinstance(registro_bruto, dict) else {}
        self._preencher_formulario_com_registro_dia(registro)
        horarios = extrair_horarios_do_registro_dia(registro)
        for campo, widget in self._widgets_horarios.items():
            widget.delete(0, "end")
            bruto = str(horarios.get(campo, "") or "").strip()
            widget.insert(0, normalizar_texto_horario(bruto) if bruto else "")
        check = getattr(self, "_widget_incluir_deslocamento_ft", None)
        if check is not None:
            if incluir_deslocamento_nas_horas(registro):
                check.select()
            else:
                check.deselect()
        self._atualizar_rotulo_jornada_liquida()
        self._atualizar_rotulo_contagem_relatorios_mes()
        for w in self._widgets_campos_dia.values():
            self.after(600, lambda x=w: self._executar_verificacao_ortografia(x))

    def _limpar_informacoes_dia_em_edicao(self: AplicacaoRdo) -> None:
        if not self._documento_atual:
            messagebox.showwarning(
                "Limpar dia",
                "Abra um cliente antes de limpar as informações do dia.",
                parent=self,
            )
            return
        d = self._data_em_edicao
        if not messagebox.askyesno(
            "Limpar dia",
            f"Apagar todas as informações do dia {d.strftime('%d/%m/%Y')} "
            f"({nome_dia_semana_portugues(d)})?\n\n"
            "Textos, horários e durações deste dia serão removidos.",
            parent=self,
            icon="warning",
        ):
            return
        if self._id_agendamento_salvar:
            self.after_cancel(self._id_agendamento_salvar)
            self._id_agendamento_salvar = None
        iso = d.isoformat()
        registros = self._documento_atual.setdefault("registros_diarios", {})
        registros.pop(iso, None)
        self._carregar_registro_dia_no_formulario(d)
        self._salvar_documento_agora(silencioso=True)

    def _persistir_dia_atual_no_documento(self) -> None:
        if not self._documento_atual:
            return
        iso = self._data_em_edicao.isoformat()
        registros = self._documento_atual.setdefault("registros_diarios", {})
        dados = self._montar_dicionario_dia_desde_formulario()
        if registro_de_dia_possui_conteudo(dados):
            registros[iso] = dados
        elif iso in registros:
            del registros[iso]
        atualizar_numero_folha_mes_em_registros(
            registros,
            self._data_em_edicao.year,
            self._data_em_edicao.month,
        )
