"""Verificação ortográfica em tempo real e menu de correções."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any

from rdo_diario.dicionario_ortografia_usuario import (
    adicionar_palavra,
    carregar_lista,
    conjunto_para_filtragem,
    salvar_lista,
    trecho_deve_ser_ignorado,
)
from rdo_diario.verificacao_ortografia import (
    extrair_sugestoes_do_match,
    offset_caractere_para_indice_tk,
    verificar_com_languagetool,
)

if TYPE_CHECKING:
    from rdo_diario.gui.app import AplicacaoRdo


class MixinOrtografia:
    """LanguageTool, dicionário pessoal e menu de contexto nos campos de texto."""

    TAG_ERRO_ORTOGRAFIA = "erro_ortografia"

    _widgets_campos_dia: dict[str, tk.Text]
    _ortografia_timers_por_widget: dict[int, str]
    _ortografia_job_id_por_widget: dict[int, int]
    _ortografia_alvos_por_widget: dict[int, list[dict[str, Any]]]
    _conjunto_dicionario_ortografia: set[str]

    def _ao_tecla_released_campo_relatorio(self, widget: tk.Text, evento: tk.Event) -> None:
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

    def _menu_correcoes_ortografia(self, widget: tk.Text, evento: tk.Event) -> None:
        """Menu de contexto com todas as sugestões do LanguageTool no trecho sob o cursor."""
        try:
            indice = widget.index(f"@{evento.x},{evento.y}")
        except tk.TclError:
            return
        wid = id(widget)
        alvos = self._ortografia_alvos_por_widget.get(wid) or []
        escolhido: dict[str, Any] | None = None
        for alvo in alvos:
            try:
                if widget.compare(indice, ">=", alvo["inicio"]) and widget.compare(indice, "<", alvo["fim"]):
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
        try:
            menu.tk_popup(evento.x_root, evento.y_root)
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass

    def _adicionar_ao_dicionario_e_reverificar(
        self,
        widget: tk.Text,
        trecho: str,
        indice_inicio: str,
        indice_fim: str,
    ) -> None:
        """Guarda o trecho no dicionário local e volta a analisar o campo (ignora maiúsculas)."""
        if not trecho.strip():
            return
        try:
            atual = widget.get(indice_inicio, indice_fim).strip()
        except tk.TclError:
            atual = ""
        if atual.casefold() != trecho.casefold():
            trecho = atual or trecho
        if adicionar_palavra(trecho):
            self._conjunto_dicionario_ortografia = conjunto_para_filtragem()
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
        self._executar_verificacao_ortografia(widget)

    def _abrir_dialogo_dicionario_ortografia(self) -> None:
        """Janela para listar, acrescentar e remover entradas do ficheiro JSON local."""
        topo = tk.Toplevel(self)
        topo.title("Dicionário ortográfico pessoal")
        topo.transient(self)
        topo.geometry("420x500")
        ttk.Label(
            topo,
            text="Palavras e siglas que o corretor não deve marcar (comparação sem maiúsculas).",
            wraplength=380,
        ).pack(fill=tk.X, padx=10, pady=(10, 4))
        moldura = ttk.Frame(topo, padding=8)
        moldura.pack(fill=tk.BOTH, expand=True)
        barra = ttk.Scrollbar(moldura)
        lista = tk.Listbox(moldura, height=16, yscrollcommand=barra.set, font=("Segoe UI", 10))
        barra.config(command=lista.yview)
        lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        for item in carregar_lista():
            lista.insert(tk.END, item)
        linha = ttk.Frame(topo, padding=(10, 0))
        linha.pack(fill=tk.X)
        ttk.Label(linha, text="Nova entrada:").pack(side=tk.LEFT)
        entrada = ttk.Entry(linha, width=32)
        entrada.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

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
            entrada.delete(0, tk.END)

        def remover_selecionados() -> None:
            for i in reversed(lista.curselection()):
                lista.delete(i)

        botoes = ttk.Frame(topo, padding=10)
        botoes.pack(fill=tk.X)
        ttk.Button(linha, text="Adicionar", command=acrescentar).pack(side=tk.LEFT)
        ttk.Button(botoes, text="Remover selecionado(s)", command=remover_selecionados).pack(
            side=tk.LEFT, padx=(0, 8)
        )

        def guardar_e_fechar() -> None:
            itens = [lista.get(i) for i in range(lista.size())]
            salvar_lista(itens)
            self._conjunto_dicionario_ortografia = conjunto_para_filtragem()
            self._verificar_ortografia_todos_campos_relatorio()
            topo.destroy()

        ttk.Button(botoes, text="Guardar e fechar", command=guardar_e_fechar).pack(side=tk.RIGHT)
        ttk.Button(botoes, text="Cancelar", command=topo.destroy).pack(side=tk.RIGHT, padx=(0, 8))
        entrada.bind("<Return>", lambda _e: acrescentar())

    def _aplicar_sugestao_ortografia(
        self,
        widget: tk.Text,
        indice_inicio: str,
        indice_fim: str,
        texto_corrigido: str,
    ) -> None:
        """Substitui o trecho marcado pela sugestão escolhida e volta a verificar o campo."""
        try:
            widget.delete(indice_inicio, indice_fim)
            widget.insert(indice_inicio, texto_corrigido)
        except tk.TclError:
            return
        wid = id(widget)
        self._ortografia_alvos_por_widget.pop(wid, None)
        widget.tag_remove(self.TAG_ERRO_ORTOGRAFIA, "1.0", tk.END)
        self._agendar_salvamento_automatico()
        self._executar_verificacao_ortografia(widget)

    def _agendar_verificacao_ortografia(self, widget: tk.Text) -> None:
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

    def _executar_verificacao_ortografia(self, widget: tk.Text) -> None:
        """
        Consulta o LanguageTool em segundo plano e marca trechos com erro em vermelho.

        O texto é enviado ao serviço público (rede necessária). Veja o menu Revisão para detalhes.
        """
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
                    self._ortografia_alvos_por_widget.pop(wid, None)
                    return
                widget.tag_remove(self.TAG_ERRO_ORTOGRAFIA, "1.0", tk.END)
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
                    widget.tag_add(self.TAG_ERRO_ORTOGRAFIA, i0, i1)
                self._ortografia_alvos_por_widget[wid] = alvos

            self.after(0, aplicar_marcas)

        threading.Thread(target=trabalho_em_thread, daemon=True).start()

    def _verificar_ortografia_todos_campos_relatorio(self) -> None:
        """Dispara verificação imediata em todos os campos de texto do dia (serviço, extra, ociosidade)."""
        for _campo, widget in self._widgets_campos_dia.items():
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
            "• Erros aparecem a vermelho e sublinhados nos três campos de texto do relatório.\n"
            "• Clique com o botão direito (ou Ctrl+clique no Mac) num trecho vermelho para ver "
            "todas as sugestões de correção e aplicar uma delas.\n"
            "• Use «Dicionário pessoal» no menu Revisão para palavras e siglas que não devem ser "
            "marcadas (ficheiro local em dados_rdo).\n\n"
            "Mais informação: https://languagetool.org/",
        )
