"""Formulário do relatório diário: textos, horários e persistência no JSON."""

from __future__ import annotations

from datetime import date
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any

from rdo_diario.calculo_metricas_horas import calcular_metricas_horas_para_dia
from rdo_diario.horario_util import (
    normalizar_duracao_hhmm,
    normalizar_texto_horario,
)
from rdo_diario.schema import (
    CAMPOS_JSON_DESLOCAMENTO,
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


class MixinFormularioDia:
    """Campos de texto, horários e leitura/gravação do registro do dia."""

    _widgets_campos_dia: dict[str, tk.Text]
    _widgets_tempo_atividade: dict[str, ttk.Entry]
    _widgets_horarios: dict[str, ttk.Entry]
    _rotulo_texto_data: ttk.Label | None
    _rotulo_contagem_mes: ttk.Label | None
    _comando_validacao_entrada_hora: Any
    _comando_validacao_entrada_duracao: Any
    _data_em_edicao: date
    _documento_atual: dict[str, Any] | None
    _config_regras_horas: dict[str, Any]
    _id_agendamento_salvar: str | None
    TAG_ERRO_ORTOGRAFIA: str

    def _criar_area_com_rolagem(self, pai: tk.Widget) -> ttk.Frame:
        """
        Devolve um `Frame` interior com scroll vertical; útil para formulários longos.
        """
        externo = ttk.Frame(pai)
        externo.pack(fill=tk.BOTH, expand=True)
        tela = tk.Canvas(externo, highlightthickness=0)
        barra = ttk.Scrollbar(externo, orient=tk.VERTICAL, command=tela.yview)
        interior = ttk.Frame(tela)
        interior.bind(
            "<Configure>",
            lambda _e: tela.configure(scrollregion=tela.bbox("all")),
        )
        id_janela = tela.create_window((0, 0), window=interior, anchor="nw")

        def _ajustar_largura(_evt: tk.Event | None = None) -> None:
            tela.itemconfigure(id_janela, width=tela.winfo_width())

        tela.bind("<Configure>", _ajustar_largura)
        tela.configure(yscrollcommand=barra.set)
        tela.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra.pack(side=tk.RIGHT, fill=tk.Y)

        def _roda_mouse(evento: tk.Event) -> str:
            tela.yview_scroll(int(-1 * (evento.delta / 120)), "units")
            return "break"

        tela.bind("<Enter>", lambda _e: tela.bind_all("<MouseWheel>", _roda_mouse))
        tela.bind("<Leave>", lambda _e: tela.unbind_all("<MouseWheel>"))
        return interior

    def _criar_texto_multilinha_com_rolagem(
        self,
        pai: tk.Widget,
        *,
        altura: int = 9,
        expandir_verticalmente: bool = True,
    ) -> tk.Text:
        """
        Caixa de texto com várias linhas, barra de rolagem vertical e roda do rato.

        Se ``expandir_verticalmente`` for False, a moldura não compete por altura
        (útil para campos baixos e deixar espaço para ponto / outros blocos).
        """
        moldura = ttk.Frame(pai)
        if expandir_verticalmente:
            moldura.pack(fill=tk.BOTH, expand=True, pady=2)
        else:
            moldura.pack(fill=tk.X, expand=False, pady=2)
        barra = ttk.Scrollbar(moldura)
        texto = tk.Text(
            moldura,
            height=altura,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            yscrollcommand=barra.set,
        )
        barra.config(command=texto.yview)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _roda_em_texto(evento: tk.Event) -> str:
            texto.yview_scroll(int(-1 * (evento.delta / 120)), "units")
            return "break"

        texto.bind("<Enter>", lambda _e: texto.bind_all("<MouseWheel>", _roda_em_texto))
        texto.bind("<Leave>", lambda _e: texto.unbind_all("<MouseWheel>"))
        texto.tag_configure(self.TAG_ERRO_ORTOGRAFIA, foreground="#cc0000", underline=True)
        texto.bind(
            "<KeyRelease>",
            lambda e, w=texto: self._ao_tecla_released_campo_relatorio(w, e),
        )
        texto.bind("<Button-3>", lambda e, w=texto: self._menu_correcoes_ortografia(w, e))
        texto.bind("<Control-Button-1>", lambda e, w=texto: self._menu_correcoes_ortografia(w, e))
        return texto

    def _montar_linha_tempo_atividade(self, pai: tk.Widget, chave_json_tempo: str) -> None:
        """Uma linha com rótulo e campo de duração (h:mm) para extra-escopo ou ociosidade."""
        linha = ttk.Frame(pai)
        linha.pack(fill=tk.X, pady=(2, 0))
        rotulo = ROTULOS_TEMPO_ATIVIDADE_DIA[chave_json_tempo]
        ttk.Label(linha, text=rotulo + ":").pack(side=tk.LEFT, padx=(0, 6))
        entrada = ttk.Entry(
            linha,
            width=10,
            font=("Segoe UI", 10),
            validate="key",
            validatecommand=(self._comando_validacao_entrada_duracao, "%P"),
        )
        entrada.pack(side=tk.LEFT)
        entrada.bind("<KeyRelease>", self._ao_tecla_solta_campo_duracao)
        entrada.bind("<FocusOut>", lambda e, w=entrada: self._ao_sair_foco_campo_duracao(w))
        self._widgets_tempo_atividade[chave_json_tempo] = entrada

    def _montar_coluna_formulario_dia(self, coluna_formulario: ttk.Frame) -> None:
        """Monta rótulos de data, campos de texto e bloco de horários do relatório diário."""
        moldura_dia = ttk.LabelFrame(coluna_formulario, text="Relatório: ", padding=8)
        moldura_dia.pack(fill=tk.BOTH, expand=True)

        linha_data = ttk.Frame(moldura_dia)
        linha_data.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(linha_data, text="Data selecionada:").pack(side=tk.LEFT)
        self._rotulo_texto_data = ttk.Label(linha_data, text="", font=("Segoe UI", 11, "bold"))
        self._rotulo_texto_data.pack(side=tk.LEFT, padx=8)
        self._rotulo_contagem_mes = ttk.Label(
            linha_data,
            text="",
            font=("Segoe UI", 10),
            foreground="#333333",
        )
        self._rotulo_contagem_mes.pack(side=tk.LEFT, padx=(12, 0))

        campos = ttk.Frame(moldura_dia)
        campos.pack(fill=tk.BOTH, expand=True)
        for campo in CAMPOS_JSON_TEXTO_DIA:
            ttk.Label(campos, text=ROTULOS_TEXTO_DIA[campo] + ":").pack(anchor=tk.W, pady=(6, 0))
            if campo in ("registro_extra_escopo", "registro_ociosidade"):
                texto = self._criar_texto_multilinha_com_rolagem(
                    campos,
                    altura=2,
                    expandir_verticalmente=False,
                )
            else:
                texto = self._criar_texto_multilinha_com_rolagem(campos, altura=9)
            self._widgets_campos_dia[campo] = texto
            if campo == "registro_extra_escopo":
                self._montar_linha_tempo_atividade(campos, "tempo_extra_escopo")
            elif campo == "registro_ociosidade":
                self._montar_linha_tempo_atividade(campos, "tempo_ociosidade")

        self._montar_secao_horarios(campos)

    def _montar_secao_horarios(self, pai: tk.Widget) -> None:
        """Bloco de horários: linha ponto, linha deslocamento, rótulo de jornada líquida."""
        moldura = ttk.LabelFrame(
            pai,
            text="Horários — ponto e deslocamento (24h, HH:MM)",
            padding=8,
        )
        moldura.pack(fill=tk.X, pady=(14, 6))

        def par_horario(linha: ttk.Frame, chave_campo: str) -> None:
            bloco = ttk.Frame(linha)
            bloco.pack(side=tk.LEFT, padx=(0, 16), pady=2)
            ttk.Label(bloco, text=ROTULOS_HORARIO[chave_campo] + ":").pack(side=tk.LEFT, padx=(0, 4))
            ent = ttk.Entry(
                bloco,
                width=6,
                font=("Segoe UI", 10),
                validate="key",
                validatecommand=(self._comando_validacao_entrada_hora, "%P"),
            )
            ent.pack(side=tk.LEFT)
            ent.bind("<KeyRelease>", self._ao_tecla_solta_campo_hora)
            ent.bind("<FocusOut>", lambda e, w=ent: self._ao_sair_foco_campo_hora(w))
            self._widgets_horarios[chave_campo] = ent

        linha_ponto = ttk.Frame(moldura)
        linha_ponto.pack(fill=tk.X)
        ttk.Label(linha_ponto, text="Ponto:", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        for chave in CAMPOS_JSON_PONTO:
            par_horario(linha_ponto, chave)

        linha_desloc = ttk.Frame(moldura)
        linha_desloc.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(linha_desloc, text="Deslocamento:", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        for chave in CAMPOS_JSON_DESLOCAMENTO:
            par_horario(linha_desloc, chave)

    def _aplicar_formatacao_campo_entrada(self, entrada: ttk.Entry, tipo: str = "horario") -> None:
        """
        Aplica formatação automática para horários ou durações.

        tipo: "horario" (HH:MM) ou "duracao" (H:MM)
        Insere ":" automaticamente após 4 dígitos.
        """
        texto = entrada.get()
        if ":" in texto:
            return
        digitos = "".join(c for c in texto if c.isdigit())
        if len(digitos) == 4:
            normalizador = normalizar_texto_horario if tipo == "horario" else normalizar_duracao_hhmm
            normalizado = normalizador(digitos)
            if normalizado:
                entrada.delete(0, tk.END)
                entrada.insert(0, normalizado)
                entrada.icursor(tk.END)

    def _normalizar_campo_entrada(self, entrada: ttk.Entry, tipo: str = "horario") -> None:
        """
        Normaliza campo ao sair (FocusOut).

        tipo: "horario" (HH:MM) ou "duracao" (H:MM)
        Garante que o valor está no formato correto.
        """
        bruto = entrada.get().strip()
        if not bruto:
            return
        normalizador = normalizar_texto_horario if tipo == "horario" else normalizar_duracao_hhmm
        normalizado = normalizador(bruto)
        if normalizado != bruto or (bruto and not normalizado):
            entrada.delete(0, tk.END)
            if normalizado:
                entrada.insert(0, normalizado)

    def _ao_tecla_solta_campo_hora(self, evento: tk.Event) -> None:
        """Após digitar hora: tenta inserir «:» após 4 dígitos, atualiza total e agenda save."""
        widget = evento.widget
        if isinstance(widget, ttk.Entry) and widget in self._widgets_horarios.values():
            self.after_idle(lambda e=widget: self._aplicar_formatacao_campo_entrada(e, "horario"))
        self._atualizar_rotulo_jornada_liquida()
        self._agendar_salvamento_automatico()

    def _ao_sair_foco_campo_hora(self, entrada: ttk.Entry) -> None:
        """Ao sair do campo, normaliza o valor e atualiza totais."""
        self._normalizar_campo_entrada(entrada, "horario")
        self._atualizar_rotulo_jornada_liquida()
        self._agendar_salvamento_automatico()

    def _ao_tecla_solta_campo_duracao(self, evento: tk.Event) -> None:
        """Normaliza duração após quatro dígitos (ex.: 0130 → 1:30) e agenda salvamento."""
        widget = evento.widget
        if isinstance(widget, ttk.Entry) and widget in self._widgets_tempo_atividade.values():
            self.after_idle(lambda e=widget: self._aplicar_formatacao_campo_entrada(e, "duracao"))
        self._agendar_salvamento_automatico()

    def _ao_sair_foco_campo_duracao(self, entrada: ttk.Entry) -> None:
        """Ao sair do campo, aplica normalização de duração h:mm."""
        self._normalizar_campo_entrada(entrada, "duracao")
        self._agendar_salvamento_automatico()

    def _atualizar_rotulo_jornada_liquida(self) -> None:
        """Mantém as métricas do painel do calendário sincronizadas com os horários digitados."""
        self._atualizar_painel_metricas_horas()

    def _payload_formulario_dia_sem_contagem_mes(self) -> dict[str, Any]:
        """
        Lê textos e horários do formulário do dia atual, sem ``numero``/``folha``.

        Usado na contagem do mês para evitar recursão com o payload completo.
        """
        saida: dict[str, Any] = {}
        for chave, widget in self._widgets_campos_dia.items():
            saida[chave] = widget.get("1.0", tk.END).strip()
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
        """Payload completo do dia para gravar no JSON, incluindo número e folha no mês."""
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
        """Preenche textos do dia a partir de um dicionário de registro."""
        for campo, widget in self._widgets_campos_dia.items():
            valor = str(registro.get(campo, "") or "")
            widget.delete("1.0", tk.END)
            widget.insert("1.0", valor)
        for campo, widget in self._widgets_tempo_atividade.items():
            widget.delete(0, tk.END)
            bruto = str(registro.get(campo, "") or "").strip()
            widget.insert(0, normalizar_duracao_hhmm(bruto) if bruto else "")

    def _carregar_registro_dia_no_formulario(self: AplicacaoRdo, dia: date) -> None:
        """Carrega o registro ISO do dia nos widgets (texto + horários normalizados)."""
        if not self._documento_atual:
            return
        iso = dia.isoformat()
        registros = self._documento_atual.setdefault("registros_diarios", {})
        registro_bruto = registros.get(iso) if isinstance(registros.get(iso), dict) else {}
        registro = registro_bruto if isinstance(registro_bruto, dict) else {}
        self._preencher_formulario_com_registro_dia(registro)
        horarios = extrair_horarios_do_registro_dia(registro)
        for campo, widget in self._widgets_horarios.items():
            widget.delete(0, tk.END)
            bruto = str(horarios.get(campo, "") or "").strip()
            widget.insert(0, normalizar_texto_horario(bruto) if bruto else "")
        self._atualizar_rotulo_jornada_liquida()
        self._atualizar_rotulo_contagem_relatorios_mes()
        for w in self._widgets_campos_dia.values():
            self.after(600, lambda x=w: self._executar_verificacao_ortografia(x))

    def _limpar_informacoes_dia_em_edicao(self: AplicacaoRdo) -> None:
        """Apaga textos, horários e registro JSON do dia selecionado no calendário."""
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
        """Escreve ou remove o registro do dia atual em `registros_diarios` conforme o conteúdo."""
        if not self._documento_atual:
            return
        iso = self._data_em_edicao.isoformat()
        registros = self._documento_atual.setdefault("registros_diarios", {})
        dados = self._montar_dicionario_dia_desde_formulario()
        if registro_de_dia_possui_conteudo(dados):
            registros[iso] = dados
        elif iso in registros:
            del registros[iso]
