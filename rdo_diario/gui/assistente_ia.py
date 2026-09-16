"""Aba do assistente IA para rascunho e reescrita do relatório diário."""

from __future__ import annotations

import threading
import tkinter as tk
from contextlib import suppress
from copy import deepcopy
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from rdo_diario.gui.combo_suspenso import configurar_combo_ctk_aprimorado
from rdo_diario.gui.desfazer_refazer import preparar_widget_edicao
from rdo_diario.gui.ia_configuracoes import DialogoConfiguracoesIa
from rdo_diario.gui.tema import (
    COR_AVISO,
    COR_PRIMARIA,
    COR_PRIMARIA_HOVER,
    COR_SUCESSO,
    COR_TEXTO_SECUNDARIO,
    FONT_CONTAGEM_MES,
    FONT_DATA_SELECIONADA,
    FONT_INTERFACE,
    opcoes_botao_ctk,
    opcoes_caixa_texto_ctk,
    opcoes_combo_ctk,
    texto_interno_campo,
)
from rdo_diario.ia_service import (
    ErroAssistenteIa,
    montar_prompt_reescrita_diario,
    prompt_enviado_e_obsoleto,
    reescrever_rascunho_diario,
)
from rdo_diario.ia_settings import carregar_config_ia

_DESTINOS_CAMPO_IA: dict[str, str] = {
    "Registro serviço": "registro_servico",
    "Registro extra-escopo": "registro_extra_escopo",
    "Registro ociosidade": "registro_ociosidade",
}


class MixinAssistenteIa:
    """Comportamento da aba Assistente IA."""

    _documento_atual: dict[str, Any] | None
    _data_em_edicao: Any
    _widgets_campos_dia: dict[str, ctk.CTkTextbox]
    _tabview: ctk.CTkTabview | None
    _id_agendamento_salvar: str | None

    def _montar_aba_assistente_ia(self, pai: ctk.CTkBaseClass) -> None:
        grupo_ia, cabecalho, corpo = self._criar_grupo_ctk(pai, "Assistente IA", compacto=True)
        grupo_ia.pack(fill="both", expand=True)
        corpo.grid_columnconfigure(0, weight=1)
        corpo.grid_rowconfigure(1, weight=1)
        corpo.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text="Data selecionada:",
            anchor="w",
            font=FONT_INTERFACE,
        ).pack(side="left", padx=(16, 0))
        self._rotulo_texto_data_ia = ctk.CTkLabel(
            cabecalho,
            text="",
            font=FONT_DATA_SELECIONADA,
            anchor="w",
        )
        self._rotulo_texto_data_ia.pack(side="left", padx=(6, 0))
        self._rotulo_contagem_mes_ia = ctk.CTkLabel(
            cabecalho,
            text="",
            font=FONT_CONTAGEM_MES,
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self._rotulo_contagem_mes_ia.pack(side="left", padx=(12, 0))

        ctk.CTkLabel(corpo, text="Rascunho do dia:", font=FONT_INTERFACE, anchor="w").grid(
            row=0, column=0, sticky="sw", pady=(0, 4)
        )
        self._widget_ia_rascunho = ctk.CTkTextbox(corpo, **opcoes_caixa_texto_ctk(altura_px=200))
        preparar_widget_edicao(self._widget_ia_rascunho)
        self._widget_ia_rascunho.grid(row=1, column=0, sticky="nsew")

        botoes = ctk.CTkFrame(corpo, fg_color="transparent")
        botoes.grid(row=2, column=0, sticky="ew", pady=(8, 8))
        self._botao_ia_reescrever = ctk.CTkButton(
            botoes,
            text="Reescrever com Gemini",
            width=180,
            fg_color=COR_PRIMARIA,
            hover_color=COR_PRIMARIA_HOVER,
            command=self._reescrever_rascunho_ia,
            **opcoes_botao_ctk(),
        )
        self._botao_ia_reescrever.pack(side="left")
        self._rotulo_ia_status = ctk.CTkLabel(
            botoes,
            text="Rascunho salvo localmente.",
            font=FONT_INTERFACE,
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
            justify="left",
        )
        self._rotulo_ia_status.pack(side="left", padx=(12, 0))

        ctk.CTkLabel(
            corpo,
            text="Texto reescrito (editável):",
            font=FONT_INTERFACE,
            anchor="w",
        ).grid(row=3, column=0, sticky="sw", pady=(0, 4))
        self._widget_ia_saida = ctk.CTkTextbox(corpo, **opcoes_caixa_texto_ctk(altura_px=240))
        preparar_widget_edicao(self._widget_ia_saida)
        self._widget_ia_saida.grid(row=4, column=0, sticky="nsew")

        rodape = ctk.CTkFrame(corpo, fg_color="transparent")
        rodape.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        ctk.CTkLabel(rodape, text="Usar no campo:", font=FONT_INTERFACE).pack(side="left", padx=(0, 6))
        self._combo_ia_destino = ctk.CTkComboBox(
            rodape,
            values=list(_DESTINOS_CAMPO_IA.keys()),
            **opcoes_combo_ctk(largura=220),
        )
        self._combo_ia_destino.pack(side="left", padx=(0, 8))
        configurar_combo_ctk_aprimorado(self._combo_ia_destino)
        self._combo_ia_destino.set("Registro serviço")
        ctk.CTkButton(
            rodape,
            text="Usar este texto",
            width=150,
            fg_color=COR_PRIMARIA,
            hover_color=COR_PRIMARIA_HOVER,
            command=self._usar_texto_ia_no_relatorio,
            **opcoes_botao_ctk(),
        ).pack(side="left")

        for widget in (self._widget_ia_rascunho, self._widget_ia_saida):
            self._ligar_ortografia_caixa(widget)
            texto_interno_campo(widget).bind("<KeyRelease>", self._ao_alterar_texto_ia, add="+")

        self._ia_online = None
        self._ia_ultimo_uso_chave = ""
        self._ia_ultimo_modelo = ""
        self._ia_ultimo_prompt_id = ""
        self._ia_ultimo_prompt_nome = ""
        self._ia_ultimo_prompt_enviado = ""
        self._ia_ultimo_historico_usado = 0
        self._ia_requisicao_em_andamento = False
        self._atualizar_rotulo_data_selecionada()
        self._atualizar_rotulo_contagem_relatorios_mes()

    def _ao_alterar_texto_ia(self, _evento=None) -> None:
        if getattr(self, "_ia_online", None) is False:
            self._definir_status_ia(
                "Offline no momento. O rascunho continua salvo localmente para tentar depois.",
                tipo="offline",
            )
        else:
            self._definir_status_ia("Rascunho salvo localmente.", tipo="neutro")
        self._agendar_salvamento_automatico()

    def _definir_status_ia(self, texto: str, *, tipo: str = "neutro") -> None:
        rotulo = getattr(self, "_rotulo_ia_status", None)
        if rotulo is None:
            return
        cor = COR_TEXTO_SECUNDARIO
        if tipo == "sucesso":
            cor = COR_SUCESSO
        elif tipo in {"aviso", "offline"}:
            cor = COR_AVISO
        with suppress(tk.TclError):
            rotulo.configure(text=texto, text_color=cor)

    def _abrir_configuracoes_ia(self) -> None:
        DialogoConfiguracoesIa(self, ao_salvar=self._apos_salvar_configuracoes_ia)

    def _apos_salvar_configuracoes_ia(self) -> None:
        self._definir_status_ia("Configurações Gemini atualizadas.", tipo="sucesso")

    def _montar_texto_conversa_api_ia(self) -> str:
        """Monta o texto legível da última troca com a API no dia em edição."""
        if hasattr(self, "_persistir_dia_atual_no_documento"):
            with suppress(AttributeError, KeyError, TypeError, ValueError, OSError):
                self._persistir_dia_atual_no_documento()

        data_ref = getattr(self, "_data_em_edicao", None)
        data_txt = ""
        if data_ref is not None:
            try:
                data_txt = data_ref.strftime("%d/%m/%Y")
            except (AttributeError, TypeError, ValueError, OverflowError):
                data_txt = str(data_ref)

        payload = self._payload_ia_dia() if hasattr(self, "_payload_ia_dia") else {}
        rascunho = str(payload.get("ia_rascunho") or "").strip()
        resposta = str(payload.get("ia_ultima_resposta") or "").strip()
        prompt_salvo = str(payload.get("ia_ultimo_prompt_enviado") or "").strip()
        if prompt_enviado_e_obsoleto(prompt_salvo):
            # Envelope fixo antigo: não exibir e não reaproveitar.
            prompt_salvo = ""
            self._ia_ultimo_prompt_enviado = ""

        prompt_atual = ""
        documento = getattr(self, "_documento_atual", None)
        if documento and data_ref is not None and rascunho:
            try:
                prompt_atual = montar_prompt_reescrita_diario(
                    documento,
                    data_ref,
                    rascunho,
                    config=carregar_config_ia(),
                ).strip()
            except (AttributeError, KeyError, TypeError, ValueError, OSError, ErroAssistenteIa):
                prompt_atual = ""

        # Preferir o prompt realmente enviado (salvo). Regenerar só se estiver ausente/obsoleto.
        prompt_exibido = prompt_salvo or prompt_atual
        modelo = str(payload.get("ia_modelo") or "").strip() or "(não informado)"
        chave = str(payload.get("ia_chave_mascarada") or "").strip() or "(não informado)"
        prompt_nome = str(payload.get("ia_prompt_nome") or "").strip() or "(não informado)"
        try:
            hist = int(payload.get("ia_historico_dias_usados") or 0)
        except (TypeError, ValueError):
            hist = 0

        if not prompt_exibido and not resposta and not rascunho:
            return (
                "Nenhuma conversa com a API encontrada para o dia selecionado.\n\n"
                "Use a aba Assistente IA e clique em «Reescrever com Gemini» para gerar uma."
            )

        linhas = [
            "Conversa completa com a API Gemini",
            "=" * 48,
            f"Data do dia: {data_txt or '(sem data)'}",
            f"Modelo: {modelo}",
            f"Chave usada: {chave}",
            f"Prompt (perfil): {prompt_nome}",
            f"Dias de histórico enviados: {hist}",
            "",
            "── Prompt completo enviado à API ──",
            prompt_exibido or "(ainda não há prompt para exibir — escreva um rascunho)",
            "",
            "── Resposta da API ──",
            resposta or "(ainda não há resposta gravada)",
            "",
        ]
        return "\n".join(linhas)

    def _abrir_conversa_api_ia(self) -> None:
        texto = self._montar_texto_conversa_api_ia()
        topo = ctk.CTkToplevel(self)
        topo.title("Conversa com a API Gemini")
        topo.transient(self)
        topo.geometry("860x640")
        topo.minsize(560, 420)
        with suppress(tk.TclError):
            topo.grab_set()

        cab = ctk.CTkFrame(topo, fg_color="transparent")
        cab.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(
            cab,
            text="Última troca enviada/recebida no dia selecionado (rascunho, prompt e resposta).",
            font=FONT_INTERFACE,
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
            justify="left",
            wraplength=700,
        ).pack(side="left", fill="x", expand=True)

        caixa = ctk.CTkTextbox(topo, **opcoes_caixa_texto_ctk(altura_px=480))
        caixa.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        caixa.insert("1.0", texto)
        caixa.configure(state="disabled")

        rodape = ctk.CTkFrame(topo, fg_color="transparent")
        rodape.pack(fill="x", padx=12, pady=(0, 12))

        def _copiar() -> None:
            try:
                self.clipboard_clear()
                self.clipboard_append(texto)
                self.update_idletasks()
            except tk.TclError:
                messagebox.showwarning(
                    "Conversa API",
                    "Não foi possível copiar o texto para a área de transferência.",
                    parent=topo,
                )
                return
            messagebox.showinfo("Conversa API", "Texto copiado.", parent=topo)

        ctk.CTkButton(rodape, text="Copiar tudo", width=120, command=_copiar).pack(side="left")
        ctk.CTkButton(rodape, text="Fechar", width=100, command=topo.destroy).pack(side="right")
        topo.after(40, lambda: topo.focus_force())

    def _payload_ia_dia(self) -> dict[str, Any]:
        rascunho = (
            self._widget_ia_rascunho.get("1.0", "end").strip()
            if getattr(self, "_widget_ia_rascunho", None)
            else ""
        )
        resposta = (
            self._widget_ia_saida.get("1.0", "end").strip()
            if getattr(self, "_widget_ia_saida", None)
            else ""
        )
        prompt_enviado = getattr(self, "_ia_ultimo_prompt_enviado", "") or ""
        if prompt_enviado_e_obsoleto(prompt_enviado):
            prompt_enviado = ""
            self._ia_ultimo_prompt_enviado = ""
        return {
            "ia_rascunho": rascunho,
            "ia_ultima_resposta": resposta,
            "ia_prompt_id": getattr(self, "_ia_ultimo_prompt_id", "") or "",
            "ia_prompt_nome": getattr(self, "_ia_ultimo_prompt_nome", "") or "",
            "ia_modelo": getattr(self, "_ia_ultimo_modelo", "") or "",
            "ia_chave_mascarada": getattr(self, "_ia_ultimo_uso_chave", "") or "",
            "ia_ultimo_prompt_enviado": prompt_enviado,
            "ia_historico_dias_usados": int(getattr(self, "_ia_ultimo_historico_usado", 0) or 0),
        }

    def _preencher_campos_ia_com_registro(self, registro: dict[str, Any]) -> None:
        if getattr(self, "_widget_ia_rascunho", None) is None:
            return
        self._widget_ia_rascunho.delete("1.0", "end")
        self._widget_ia_rascunho.insert("1.0", str(registro.get("ia_rascunho", "") or ""))
        self._widget_ia_saida.delete("1.0", "end")
        self._widget_ia_saida.insert("1.0", str(registro.get("ia_ultima_resposta", "") or ""))
        self._ia_ultimo_uso_chave = str(registro.get("ia_chave_mascarada", "") or "")
        self._ia_ultimo_modelo = str(registro.get("ia_modelo", "") or "")
        self._ia_ultimo_prompt_id = str(registro.get("ia_prompt_id", "") or "")
        self._ia_ultimo_prompt_nome = str(registro.get("ia_prompt_nome", "") or "")
        self._ia_ultimo_prompt_enviado = str(registro.get("ia_ultimo_prompt_enviado", "") or "")
        if prompt_enviado_e_obsoleto(self._ia_ultimo_prompt_enviado):
            self._ia_ultimo_prompt_enviado = ""
        try:
            self._ia_ultimo_historico_usado = int(registro.get("ia_historico_dias_usados") or 0)
        except (TypeError, ValueError):
            self._ia_ultimo_historico_usado = 0
        if self._ia_ultimo_uso_chave:
            self._definir_status_ia("Última reescrita carregada deste dia.", tipo="neutro")
        else:
            self._definir_status_ia("Rascunho salvo localmente.", tipo="neutro")

    def _reescrever_rascunho_ia(self) -> None:
        if self._ia_requisicao_em_andamento:
            return
        if not self._documento_atual:
            messagebox.showwarning(
                "Assistente IA",
                "Abra ou crie um projeto antes de usar a reescrita por IA.",
                parent=self,
            )
            return
        rascunho = self._widget_ia_rascunho.get("1.0", "end").strip()
        if not rascunho:
            messagebox.showwarning(
                "Assistente IA",
                "Escreva o rascunho do dia antes de pedir a reescrita.",
                parent=self,
            )
            return

        self._persistir_dia_atual_no_documento()
        documento = deepcopy(self._documento_atual)
        data_referencia = self._data_em_edicao
        config = carregar_config_ia()
        self._ia_requisicao_em_andamento = True
        self._botao_ia_reescrever.configure(state="disabled", text="Reescrevendo...")
        self._definir_status_ia("Enviando rascunho e histórico local ao Gemini...", tipo="neutro")

        def trabalhador() -> None:
            try:
                resultado = reescrever_rascunho_diario(
                    documento,
                    data_referencia,
                    rascunho,
                    config=config,
                )
                self.after(0, lambda res=resultado: self._finalizar_reescrita_ia(res, None))
            except (ErroAssistenteIa, OSError, RuntimeError, ValueError, TypeError) as exc:
                self.after(0, lambda err=exc: self._finalizar_reescrita_ia(None, err))
            except Exception as exc:  # noqa: BLE001 — erros da SDK Gemini / rede
                self.after(0, lambda err=exc: self._finalizar_reescrita_ia(None, err))

        threading.Thread(target=trabalhador, daemon=True).start()

    def _finalizar_reescrita_ia(self, resultado: dict[str, Any] | None, erro: BaseException | None) -> None:
        try:
            if not bool(self.winfo_exists()):
                return
        except tk.TclError:
            return
        self._ia_requisicao_em_andamento = False
        try:
            self._botao_ia_reescrever.configure(state="normal", text="Reescrever com Gemini")
        except tk.TclError:
            return
        if erro is not None:
            offline = isinstance(erro, ErroAssistenteIa) and bool(getattr(erro, "offline", False))
            self._ia_online = False if offline else self._ia_online
            self._definir_status_ia(
                str(erro),
                tipo="offline" if offline else "aviso",
            )
            caixa = messagebox.showwarning if offline else messagebox.showerror
            caixa("Assistente IA", str(erro), parent=self)
            return

        if not resultado:
            self._definir_status_ia("Falha inesperada ao reescrever o texto.", tipo="aviso")
            return
        self._ia_online = True
        self._widget_ia_saida.delete("1.0", "end")
        self._widget_ia_saida.insert("1.0", str(resultado.get("texto_reescrito") or ""))
        self._ia_ultimo_uso_chave = str(resultado.get("chave_mascarada") or "")
        self._ia_ultimo_modelo = str(resultado.get("modelo") or "")
        self._ia_ultimo_prompt_id = str(resultado.get("prompt_id") or "")
        self._ia_ultimo_prompt_nome = str(resultado.get("prompt_nome") or "")
        self._ia_ultimo_prompt_enviado = str(resultado.get("prompt_enviado") or "")
        try:
            self._ia_ultimo_historico_usado = int(resultado.get("historico_usado") or 0)
        except (TypeError, ValueError):
            self._ia_ultimo_historico_usado = 0
        self._definir_status_ia(
            f"Texto reescrito com sucesso usando {self._ia_ultimo_uso_chave or 'uma chave Gemini'}.",
            tipo="sucesso",
        )
        self._agendar_verificacao_ortografia(self._widget_ia_saida)
        self._agendar_salvamento_automatico()

    def _usar_texto_ia_no_relatorio(self) -> None:
        texto = self._widget_ia_saida.get("1.0", "end").strip()
        if not texto:
            messagebox.showwarning(
                "Assistente IA",
                "Não há texto reescrito para aplicar.",
                parent=self,
            )
            return
        destino_rotulo = self._combo_ia_destino.get().strip()
        campo = _DESTINOS_CAMPO_IA.get(destino_rotulo)
        if not campo:
            return
        widget = self._widgets_campos_dia.get(campo)
        if widget is None:
            return
        widget.delete("1.0", "end")
        widget.insert("1.0", texto)
        if getattr(self, "_tabview", None) is not None:
            with suppress(tk.TclError, ValueError):
                self._tabview.set("Relatórios de trabalho")
        with suppress(tk.TclError, AttributeError):
            texto_interno_campo(widget).focus_set()
        self._definir_status_ia(f"Texto aplicado em '{destino_rotulo}'.", tipo="sucesso")
        self._agendar_salvamento_automatico()
