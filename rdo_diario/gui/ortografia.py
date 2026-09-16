"""Verificação ortográfica em tempo real e menu de correções."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from rdo_diario.dicionario_ortografia_usuario import (
    adicionar_palavra,
    carregar_lista,
    conjunto_para_filtragem,
    salvar_lista,
    trecho_deve_ser_ignorado,
)
from rdo_diario.gui.tema import configurar_menu_tk, opcoes_listbox_tk_embutido, texto_interno_campo
from rdo_diario.verificacao_ortografia import (
    extrair_sugestoes_do_match,
    offset_caractere_para_indice_tk,
    verificar_com_languagetool,
)


class MixinOrtografia:
    """LanguageTool, dicionário pessoal e menu de contexto nos campos de texto."""

    TAG_ERRO_ORTOGRAFIA = "erro_ortografia"

    _widgets_campos_dia: dict[str, ctk.CTkTextbox]
    _ortografia_timers_por_widget: dict[int, str]
    _ortografia_job_id_por_widget: dict[int, int]
    _ortografia_alvos_por_widget: dict[int, list[dict[str, Any]]]
    _conjunto_dicionario_ortografia: set[str]

    def _ao_tecla_released_campo_relatorio(self, widget: ctk.CTkTextbox, evento: tk.Event) -> None:
        """Autosave e debounce da verificação ortográfica (LanguageTool) nos textos do relatório."""
        self._agendar_salvamento_automatico(evento)
        self._agendar_verificacao_ortografia(widget)

    def _rotulo_curto_menu(self, texto: str, maximo: int = 72) -> str:
        """Evita linhas demasiado longas no menu; duplica «&» para o Tk não tratar como atalho."""
        t = texto.replace("\n", " ").replace("\r", " ").strip()
        t = t.replace("&", "&&")
        if len(t) <= maximo:
            return t or " "
        return t[: maximo - 1] + "…"

    def _menu_correcoes_ortografia(self, widget: ctk.CTkTextbox, evento: tk.Event) -> None:
        """Menu de contexto com todas as sugestões do LanguageTool no trecho sob o cursor."""
        caixa = texto_interno_campo(widget)
        try:
            indice = caixa.index(f"@{evento.x},{evento.y}")
        except tk.TclError:
            return
        wid = id(widget)
        alvos = self._ortografia_alvos_por_widget.get(wid) or []
        escolhido: dict[str, Any] | None = None
        for alvo in alvos:
            try:
                if caixa.compare(indice, ">=", alvo["inicio"]) and caixa.compare(indice, "<", alvo["fim"]):
                    escolhido = alvo
                    break
            except tk.TclError:
                continue
        if not escolhido:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label=self._rotulo_curto_menu(escolhido.get("mensagem") or "Problema detectado", 100),
            state=tk.DISABLED,
        )
        menu.add_separator()
        sugestoes: list[str] = escolhido.get("sugestoes") or []
        if not sugestoes:
            menu.add_command(label="(Sem sugestão automática)", state=tk.DISABLED)
        else:
            limite_primeiro_menu = 20
            primeira = sugestoes[:limite_primeiro_menu]
            restantes = sugestoes[limite_primeiro_menu:]
            ini, fim = escolhido["inicio"], escolhido["fim"]
            for sug in primeira:
                menu.add_command(
                    label=self._rotulo_curto_menu(sug, 76),
                    command=lambda s=sug, i=ini, f=fim, w=widget: self._aplicar_sugestao_ortografia(w, i, f, s),
                )
            if restantes:
                sub = tk.Menu(menu, tearoff=0)
                menu.add_cascade(
                    label=self._rotulo_curto_menu(f"Mais sugestões ({len(restantes)})…", 40),
                    menu=sub,
                )
                for sug in restantes:
                    sub.add_command(
                        label=self._rotulo_curto_menu(sug, 76),
                        command=lambda s=sug, i=ini, f=fim, w=widget: self._aplicar_sugestao_ortografia(
                            w, i, f, s
                        ),
                    )
        menu.add_separator()
        try:
            trecho_dic = widget.get(escolhido["inicio"], escolhido["fim"]).strip()
        except tk.TclError:
            trecho_dic = ""
        if trecho_dic:
            menu.add_command(
                label=self._rotulo_curto_menu(f"Adicionar «{trecho_dic}» ao dicionário pessoal", 70),
                command=lambda w=widget, t=trecho_dic, i=escolhido["inicio"], f=escolhido["fim"]: self._adicionar_ao_dicionario_e_reverificar(
                    w, t, i, f
                ),
            )
        configurar_menu_tk(menu)
        try:
            menu.tk_popup(evento.x_root, evento.y_root)
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass

    def _adicionar_ao_dicionario_e_reverificar(
        self,
        widget: ctk.CTkTextbox,
        trecho: str,
        indice_inicio: str,
        indice_fim: str,
    ) -> None:
        """Guarda o trecho no dicionário local e remove as marcas correspondentes de imediato."""
        if not trecho.strip():
            return
        try:
            atual = widget.get(indice_inicio, indice_fim).strip()
        except tk.TclError:
            atual = ""
        if atual.casefold() != trecho.casefold():
            trecho = atual or trecho
        adicionada = adicionar_palavra(trecho)
        self._conjunto_dicionario_ortografia = conjunto_para_filtragem()
        self._remover_alvos_com_trecho(widget, trecho)
        if adicionada:
            messagebox.showinfo(
                "Dicionário pessoal",
                f"«{trecho}» foi adicionado. Os avisos para esta forma deixam de aparecer.",
                parent=self,
            )
        else:
            messagebox.showinfo(
                "Dicionário pessoal",
                f"«{trecho}» já estava no dicionário.",
                parent=self,
            )
        self._agendar_verificacao_ortografia(widget)

    def _abrir_dialogo_dicionario_ortografia(self) -> None:
        """Janela para listar, acrescentar e remover entradas do ficheiro JSON local."""
        topo = ctk.CTkToplevel(self)
        topo.title("Dicionário ortográfico pessoal")
        topo.transient(self)
        topo.geometry("440x520")
        ctk.CTkLabel(
            topo,
            text="Palavras e siglas que o corretor não deve marcar (comparação sem maiúsculas).",
            wraplength=400,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(12, 4))
        moldura = ctk.CTkFrame(topo, fg_color="transparent")
        moldura.pack(fill="both", expand=True, padx=12, pady=4)
        barra = ctk.CTkScrollbar(moldura, orientation="vertical")
        lista = tk.Listbox(
            moldura,
            height=16,
            yscrollcommand=barra.set,
            font=("Segoe UI", 10),
            **opcoes_listbox_tk_embutido(),
        )
        barra.configure(command=lista.yview)
        lista.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        for item in carregar_lista():
            lista.insert(tk.END, item)
        linha = ctk.CTkFrame(topo, fg_color="transparent")
        linha.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkLabel(linha, text="Nova entrada:", anchor="w").pack(side="left")
        entrada = ctk.CTkEntry(linha, width=220)
        entrada.pack(side="left", padx=8, fill="x", expand=True)

        def acrescentar() -> None:
            t = entrada.get().strip()
            if not t:
                return
            existentes = {lista.get(i).casefold() for i in range(lista.size())}
            if t.casefold() in existentes:
                messagebox.showinfo("Dicionário", "Esta entrada já está na lista.", parent=topo)
                return
            lista.insert(tk.END, t)
            lista.see(tk.END)
            entrada.delete(0, "end")

        def remover_selecionados() -> None:
            for i in reversed(lista.curselection()):
                lista.delete(i)

        botoes = ctk.CTkFrame(topo, fg_color="transparent")
        botoes.pack(fill="x", padx=12, pady=12)
        ctk.CTkButton(linha, text="Adicionar", width=100, command=acrescentar).pack(side="left", padx=(8, 0))
        ctk.CTkButton(botoes, text="Remover selecionado(s)", command=remover_selecionados).pack(
            side="left", padx=(0, 8)
        )

        def guardar_e_fechar() -> None:
            itens = [lista.get(i) for i in range(lista.size())]
            salvar_lista(itens)
            self._conjunto_dicionario_ortografia = conjunto_para_filtragem()
            self._verificar_ortografia_todos_campos_relatorio()
            topo.destroy()

        ctk.CTkButton(botoes, text="Guardar e fechar", command=guardar_e_fechar).pack(side="right")
        ctk.CTkButton(botoes, text="Cancelar", command=topo.destroy).pack(side="right", padx=(0, 8))
        entrada.bind("<Return>", lambda _e: acrescentar())

    def _offset_de_indice_tk(self, widget: ctk.CTkTextbox, indice: str) -> int | None:
        """Posição em caracteres (0-based) do índice Tk no texto atual do campo."""
        try:
            return len(widget.get("1.0", indice))
        except tk.TclError:
            return None

    def _invalidar_jobs_ortografia_em_voo(self, widget: ctk.CTkTextbox) -> None:
        """Descarta resultados de pedidos LanguageTool ainda em curso neste campo."""
        wid = id(widget)
        self._ortografia_job_id_por_widget[wid] = self._ortografia_job_id_por_widget.get(wid, 0) + 1

    def _repintar_marcas_ortografia(self, widget: ctk.CTkTextbox, alvos: list[dict[str, Any]]) -> None:
        """Substitui as marcas vermelhas pelas faixas em ``alvos`` (sem consultar a API)."""
        caixa = texto_interno_campo(widget)
        try:
            caixa.tag_remove(self.TAG_ERRO_ORTOGRAFIA, "1.0", tk.END)
        except tk.TclError:
            return
        validos: list[dict[str, Any]] = []
        for alvo in alvos:
            try:
                caixa.tag_add(self.TAG_ERRO_ORTOGRAFIA, alvo["inicio"], alvo["fim"])
            except tk.TclError:
                continue
            validos.append(alvo)
        self._ortografia_alvos_por_widget[id(widget)] = validos

    def _remover_alvos_com_trecho(self, widget: ctk.CTkTextbox, trecho: str) -> None:
        """Tira as marcas cujo texto coincide com ``trecho`` (sem diferenciar maiúsculas)."""
        chave = trecho.casefold().strip()
        if not chave:
            return
        wid = id(widget)
        restantes: list[dict[str, Any]] = []
        for alvo in self._ortografia_alvos_por_widget.get(wid) or []:
            try:
                atual = widget.get(alvo["inicio"], alvo["fim"])
            except tk.TclError:
                continue
            if atual.casefold().strip() == chave:
                continue
            restantes.append(alvo)
        self._invalidar_jobs_ortografia_em_voo(widget)
        self._repintar_marcas_ortografia(widget, restantes)

    def _atualizar_alvos_apos_substituicao(
        self,
        widget: ctk.CTkTextbox,
        offset: int,
        comprimento_antigo: int,
        comprimento_novo: int,
        alvos_offsets: list[tuple[int, int, dict[str, Any]]],
    ) -> None:
        """Recalcula índices das marcas restantes após uma correção local."""
        try:
            texto_novo = widget.get("1.0", "end-1c")
        except tk.TclError:
            return
        delta = comprimento_novo - comprimento_antigo
        fim_antigo = offset + comprimento_antigo
        novos: list[dict[str, Any]] = []
        for o0, o1, alvo in alvos_offsets:
            if not (o1 <= offset or o0 >= fim_antigo):
                continue
            if o0 >= fim_antigo:
                o0 += delta
                o1 += delta
            if o0 < 0 or o1 > len(texto_novo) or o0 >= o1:
                continue
            novos.append(
                {
                    "inicio": offset_caractere_para_indice_tk(texto_novo, o0),
                    "fim": offset_caractere_para_indice_tk(texto_novo, o1),
                    "mensagem": alvo.get("mensagem") or "",
                    "sugestoes": list(alvo.get("sugestoes") or []),
                }
            )
        self._repintar_marcas_ortografia(widget, novos)

    def _aplicar_sugestao_ortografia(
        self,
        widget: ctk.CTkTextbox,
        indice_inicio: str,
        indice_fim: str,
        texto_corrigido: str,
    ) -> None:
        """Substitui o trecho marcado e ajusta as outras marcas sem nova consulta à API."""
        offset = self._offset_de_indice_tk(widget, indice_inicio)
        try:
            trecho_antigo = widget.get(indice_inicio, indice_fim)
        except tk.TclError:
            return
        if offset is None:
            return
        alvos_offsets: list[tuple[int, int, dict[str, Any]]] = []
        for alvo in self._ortografia_alvos_por_widget.get(id(widget)) or []:
            o0 = self._offset_de_indice_tk(widget, alvo["inicio"])
            o1 = self._offset_de_indice_tk(widget, alvo["fim"])
            if o0 is None or o1 is None or o0 >= o1:
                continue
            alvos_offsets.append((o0, o1, alvo))
        try:
            widget.delete(indice_inicio, indice_fim)
            widget.insert(indice_inicio, texto_corrigido)
        except tk.TclError:
            return
        self._invalidar_jobs_ortografia_em_voo(widget)
        self._atualizar_alvos_apos_substituicao(
            widget,
            offset,
            len(trecho_antigo),
            len(texto_corrigido),
            alvos_offsets,
        )
        self._agendar_salvamento_automatico()
        self._agendar_verificacao_ortografia(widget)

    def _agendar_verificacao_ortografia(self, widget: ctk.CTkTextbox) -> None:
        """Agenda verificação após pausa na digitação (evita exceder o limite gratuito da API)."""
        wid = id(widget)
        anterior = self._ortografia_timers_por_widget.pop(wid, None)
        if anterior is not None:
            try:
                self.after_cancel(anterior)
            except tk.TclError:
                pass
        self._ortografia_timers_por_widget[wid] = self.after(
            2800,
            lambda w=widget: self._executar_verificacao_ortografia(w),
        )

    def _executar_verificacao_ortografia(self, widget: ctk.CTkTextbox) -> None:
        """
        Consulta o LanguageTool em segundo plano e marca trechos com erro em vermelho.

        O texto é enviado ao serviço público (rede necessária). Veja o menu Revisão para detalhes.
        """
        caixa = texto_interno_campo(widget)
        wid = id(widget)
        self._ortografia_timers_por_widget.pop(wid, None)
        try:
            texto_ref = widget.get("1.0", "end-1c")
        except tk.TclError:
            return
        novo_id = self._ortografia_job_id_por_widget.get(wid, 0) + 1
        self._ortografia_job_id_por_widget[wid] = novo_id
        job_local = novo_id

        def trabalho_em_thread() -> None:
            correspondencias = verificar_com_languagetool(texto_ref)

            def aplicar_marcas() -> None:
                try:
                    if not widget.winfo_exists():
                        return
                except tk.TclError:
                    return
                if self._ortografia_job_id_por_widget.get(wid, 0) != job_local:
                    return
                try:
                    atual = widget.get("1.0", "end-1c")
                except tk.TclError:
                    return
                if atual != texto_ref:
                    return
                if correspondencias is None:
                    return
                caixa.tag_remove(self.TAG_ERRO_ORTOGRAFIA, "1.0", tk.END)
                alvos: list[dict[str, Any]] = []
                conj_dic = self._conjunto_dicionario_ortografia
                for m in correspondencias:
                    try:
                        o = int(m.get("offset", 0))
                        lg = int(m.get("length", 0))
                    except (TypeError, ValueError):
                        continue
                    if lg <= 0:
                        continue
                    if o + lg > len(atual):
                        continue
                    if trecho_deve_ser_ignorado(atual, o, lg, conj_dic):
                        continue
                    i0 = offset_caractere_para_indice_tk(atual, o)
                    i1 = offset_caractere_para_indice_tk(atual, o + lg)
                    mensagem = str(m.get("message") or "").strip().replace("\n", " ")
                    sugestoes = extrair_sugestoes_do_match(m)
                    alvos.append(
                        {
                            "inicio": i0,
                            "fim": i1,
                            "mensagem": mensagem,
                            "sugestoes": sugestoes,
                        }
                    )
                    caixa.tag_add(self.TAG_ERRO_ORTOGRAFIA, i0, i1)
                self._ortografia_alvos_por_widget[wid] = alvos

            self.after(0, aplicar_marcas)

        threading.Thread(target=trabalho_em_thread, daemon=True).start()

    def _iter_caixas_texto_ortografia(self) -> list[ctk.CTkTextbox]:
        """Campos multilinha com LanguageTool: relatório diário e assistente IA."""
        caixas = list(self._widgets_campos_dia.values())
        for attr in ("_widget_ia_rascunho", "_widget_ia_saida"):
            widget = getattr(self, attr, None)
            if widget is not None:
                caixas.append(widget)
        return caixas

    def _verificar_ortografia_todos_campos_relatorio(self) -> None:
        """Dispara verificação imediata nos campos de texto do relatório e do assistente IA."""
        for widget in self._iter_caixas_texto_ortografia():
            wid = id(widget)
            anterior = self._ortografia_timers_por_widget.pop(wid, None)
            if anterior is not None:
                try:
                    self.after_cancel(anterior)
                except tk.TclError:
                    pass
            self._executar_verificacao_ortografia(widget)

    def _mostrar_info_verificacao_ortografia(self) -> None:
        messagebox.showinfo(
            "Verificação ortográfica",
            "A revisão usa o serviço público gratuito LanguageTool (ortografia e gramática em "
            "português do Brasil).\n\n"
            "• O texto dos relatórios é enviado pela internet para análise.\n"
            "• Há limite de uso por IP; a verificação automática só corre alguns segundos após "
            "parar de digitar.\n"
            "• Erros aparecem a vermelho e sublinhados nos campos de texto do relatório, do "
            "Assistente IA e do texto do prompt nas Configurações Gemini.\n"
            "• Clique com o botão direito (ou Ctrl+clique no Mac) num trecho vermelho para ver "
            "todas as sugestões de correção e aplicar uma delas.\n"
            "• Use «Dicionário pessoal» no menu Revisão para palavras e siglas que não devem ser "
            "marcadas (ficheiro local em dados_rdo).\n\n"
            "Mais informação: https://languagetool.org/",
        )
