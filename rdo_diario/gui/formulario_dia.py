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
    CAMPOS_JSON_TEXTO_DIA,
    CHAVE_JSON_BATIDAS_PONTO,
    CHAVE_JSON_FOLHA_RELATORIO_MES,
    CHAVE_JSON_METRICAS_HORAS,
    CHAVE_JSON_NUMERO_RELATORIO_MES,
    ROTULOS_HORARIO,
    ROTULOS_TEMPO_ATIVIDADE_DIA,
    ROTULOS_TEXTO_DIA,
    aplicar_metadados_data_no_registro_diario,
    extrair_horarios_do_registro_dia,
    nome_dia_semana_portugues,
    registro_de_dia_possui_conteudo,
)

if TYPE_CHECKING:
    from rdo_diario.gui.app import AplicacaoRdo

_ALTURA_TEXTO_GRANDE = 200
_ALTURA_TEXTO_PEQUENO = 56
_LARGURA_CAMPO_ENTRADA = 60


class MixinFormularioDia:
    """Campos de texto, horários e leitura/gravação do registro do dia."""

    _widgets_campos_dia: dict[str, ctk.CTkTextbox]
    _widgets_tempo_atividade: dict[str, ctk.CTkEntry]
    _widgets_horarios: dict[str, ctk.CTkEntry]
    _rotulo_texto_data: ctk.CTkLabel | None
    _rotulo_contagem_mes: ctk.CTkLabel | None
    _comando_validacao_entrada_hora: Any
    _comando_validacao_entrada_duracao: Any
    _data_em_edicao: date
    _documento_atual: dict[str, Any] | None
    _config_regras_horas: dict[str, Any]
    _id_agendamento_salvar: str | None
    TAG_ERRO_ORTOGRAFIA: str

    def _criar_grupo_ctk(self, pai: ctk.CTkBaseClass, titulo: str) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        return criar_painel_ctk_com_titulo(pai, titulo)

    def _criar_texto_multilinha(
        self,
        pai: ctk.CTkBaseClass,
        *,
        altura_px: int = _ALTURA_TEXTO_GRANDE,
        expandir_verticalmente: bool = True,
    ) -> ctk.CTkTextbox:
        texto = ctk.CTkTextbox(pai, **opcoes_caixa_texto_ctk(altura_px=altura_px))
        if expandir_verticalmente:
            texto.pack(fill="both", expand=True, pady=4)
        else:
            texto.pack(fill="x", expand=False, pady=4)

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
        return texto

    def _montar_linha_tempo_atividade(self, pai: ctk.CTkBaseClass, chave_json_tempo: str) -> None:
        linha = ctk.CTkFrame(pai, fg_color="transparent")
        linha.pack(fill="x", pady=(4, 0))
        rotulo = ROTULOS_TEMPO_ATIVIDADE_DIA[chave_json_tempo]
        ctk.CTkLabel(linha, text=rotulo + ":", anchor="w", font=FONT_INTERFACE).pack(side="left", padx=(0, 6))
        entrada = ctk.CTkEntry(linha, **opcoes_campo_entrada_ctk(largura=_LARGURA_CAMPO_ENTRADA))
        entrada.pack(side="left")
        aplicar_validacao_entrada_ctk(entrada, self._comando_validacao_entrada_duracao)
        entrada.bind("<KeyRelease>", self._ao_tecla_solta_campo_duracao)
        entrada.bind("<FocusOut>", lambda _e, w=entrada: self._ao_sair_foco_campo_duracao(w))
        self._widgets_tempo_atividade[chave_json_tempo] = entrada

    def _montar_coluna_formulario_dia(self, coluna_formulario: ctk.CTkBaseClass) -> None:
        grupo_dia, moldura_dia = self._criar_grupo_ctk(coluna_formulario, "Relatório")
        grupo_dia.pack(fill="both", expand=True)

        linha_data = ctk.CTkFrame(moldura_dia, fg_color="transparent")
        linha_data.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(linha_data, text="Data selecionada:", anchor="w", font=FONT_INTERFACE).pack(side="left")
        self._rotulo_texto_data = ctk.CTkLabel(
            linha_data,
            text="",
            font=FONT_DATA_SELECIONADA,
            anchor="w",
        )
        self._rotulo_texto_data.pack(side="left", padx=8)
        self._rotulo_contagem_mes = ctk.CTkLabel(
            linha_data,
            text="",
            font=FONT_CONTAGEM_MES,
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self._rotulo_contagem_mes.pack(side="left", padx=(12, 0))

        campos = ctk.CTkFrame(moldura_dia, fg_color="transparent")
        campos.pack(fill="both", expand=True)
        for campo in CAMPOS_JSON_TEXTO_DIA:
            ctk.CTkLabel(campos, text=ROTULOS_TEXTO_DIA[campo] + ":", anchor="w", font=FONT_INTERFACE).pack(
                anchor="w", pady=(8, 0)
            )
            if campo in ("registro_extra_escopo", "registro_ociosidade"):
                texto = self._criar_texto_multilinha(
                    campos,
                    altura_px=_ALTURA_TEXTO_PEQUENO,
                    expandir_verticalmente=False,
                )
            else:
                texto = self._criar_texto_multilinha(campos, altura_px=_ALTURA_TEXTO_GRANDE)
            self._widgets_campos_dia[campo] = texto
            if campo == "registro_extra_escopo":
                self._montar_linha_tempo_atividade(campos, "tempo_extra_escopo")
            elif campo == "registro_ociosidade":
                self._montar_linha_tempo_atividade(campos, "tempo_ociosidade")

        self._montar_secao_horarios(campos)

    def _montar_secao_horarios(self, pai: ctk.CTkBaseClass) -> None:
        grupo_horarios, moldura = self._criar_grupo_ctk(
            pai,
            "Horários — ponto e deslocamento (24h, HH:MM)",
        )
        grupo_horarios.pack(fill="x", pady=(14, 6))

        def par_horario(linha: ctk.CTkFrame, chave_campo: str, *, espacamento_direita: int = 16) -> None:
            bloco = ctk.CTkFrame(linha, fg_color="transparent")
            bloco.pack(side="left", padx=(0, espacamento_direita), pady=2)
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

        linha_ponto = ctk.CTkFrame(moldura, fg_color="transparent")
        linha_ponto.pack(fill="x")
        ctk.CTkLabel(linha_ponto, text="Ponto:", font=FONT_GRUPO, anchor="w").pack(
            side="left", padx=(0, 6)
        )
        for chave in CAMPOS_JSON_PONTO:
            par_horario(linha_ponto, chave, espacamento_direita=8)

        linha_desloc = ctk.CTkFrame(moldura, fg_color="transparent")
        linha_desloc.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(
            linha_desloc,
            text="Deslocamento:",
            font=FONT_GRUPO,
            anchor="w",
        ).pack(side="left", padx=(0, 10))
        for chave in CAMPOS_JSON_DESLOCAMENTO:
            par_horario(linha_desloc, chave)

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
