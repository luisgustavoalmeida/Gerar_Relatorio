"""Janela principal: orquestra menu, formulário, calendário e ortografia."""

from __future__ import annotations

import json
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from rdo_diario.config_horas import (
    carregar_config_regras_horas,
    garantir_arquivo_config_regras_existe,
)
from rdo_diario.dicionario_ortografia_usuario import conjunto_para_filtragem
from rdo_diario.gerar_excel_relatorios import gerar_relatorios_excel
from rdo_diario.horario_util import (
    texto_duracao_permitido_na_digitacao,
    texto_horario_permitido_na_digitacao,
)
from rdo_diario.paths import ARQUIVO_MODELO_CABECALHO_JSON, PASTA_DADOS_RDO
from rdo_diario.schema import (
    CAMPOS_JSON_CABECALHO,
    CHAVE_JSON_CONTRATANTE,
    CHAVE_JSON_NATUREZA_SERVICO,
    ROTULOS_CABECALHO,
)
from rdo_diario.storage import (
    carregar_documento_json,
    carregar_ou_criar_cliente,
    listar_clientes_salvos,
    obter_documento_cliente_inicial,
    salvar_documento_json,
    salvar_memoria_ultimo_cliente,
)

from rdo_diario.gui.calendario import MixinCalendario
from rdo_diario.gui.formulario_dia import MixinFormularioDia
from rdo_diario.gui.menu import MixinMenu
from rdo_diario.gui.ortografia import MixinOrtografia


class AplicacaoRdo(
    tk.Tk,
    MixinMenu,
    MixinCalendario,
    MixinFormularioDia,
    MixinOrtografia,
):
    """Janela principal: seleção de cliente, abas de dados fixos e relatório diário."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Relatório de atividades diárias")
        self.geometry("980x760")
        self.minsize(720, 600)

        self._documento_atual: dict[str, Any] | None = None
        self._caminho_arquivo_atual: Path | None = None
        self._data_em_edicao: date = date.today()
        self._widgets_cabecalho: dict[str, ttk.Entry] = {}
        self._widgets_campos_dia: dict[str, tk.Text] = {}
        self._widgets_tempo_atividade: dict[str, ttk.Entry] = {}
        self._widgets_horarios: dict[str, ttk.Entry] = {}
        self._id_agendamento_salvar: str | None = None
        self._widget_calendario = None
        self._combo_selecao_cliente: ttk.Combobox | None = None
        self._mapa_rotulo_para_caminho: dict[str, Path] = {}
        self._rotulo_texto_data = None
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

    def _montar_barra_cliente(self) -> None:
        """Barra superior: seleção de cliente (contratante + natureza)."""
        barra = ttk.Frame(self, padding=6)
        barra.pack(fill=tk.X)
        ttk.Label(barra, text="Cliente (contratante + natureza):").pack(side=tk.LEFT, padx=(0, 6))
        self._combo_selecao_cliente = ttk.Combobox(barra, width=70, state="readonly")
        self._combo_selecao_cliente.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self._combo_selecao_cliente.bind("<<ComboboxSelected>>", self._ao_trocar_cliente_combo)

    def _montar_corpo_janela(self) -> None:
        """Abas «Dados fixos» e «Relatórios», com calendário na segunda."""
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        aba_cabecalho = ttk.Frame(notebook)
        aba_registros = ttk.Frame(notebook)
        notebook.add(aba_cabecalho, text="Cabeçalhos")
        notebook.add(aba_registros, text="Relatórios de trabalho")

        dica_cab = ttk.Label(
            aba_cabecalho,
            text="Informações destinadas ao cabeçalhos das planilha (RDO e FT).",
            wraplength=800,
        )
        dica_cab.pack(fill=tk.X, padx=8, pady=(8, 4))
        area_rolavel = self._criar_area_com_rolagem(aba_cabecalho)
        form_cab = ttk.Frame(area_rolavel, padding=12)
        form_cab.pack(fill=tk.BOTH, expand=True)
        for indice, campo in enumerate(CAMPOS_JSON_CABECALHO):
            ttk.Label(form_cab, text=ROTULOS_CABECALHO[campo] + ":").grid(
                row=indice, column=0, sticky=tk.NW, pady=4, padx=(0, 10)
            )
            entrada = ttk.Entry(form_cab, width=70)
            entrada.grid(row=indice, column=1, sticky=tk.EW, pady=4)
            entrada.bind("<KeyRelease>", self._agendar_salvamento_automatico)
            self._widgets_cabecalho[campo] = entrada
        form_cab.columnconfigure(1, weight=1)

        painel = ttk.PanedWindow(aba_registros, orient=tk.HORIZONTAL)
        painel.pack(fill=tk.BOTH, expand=True, padx=4, pady=8)

        coluna_formulario = ttk.Frame(painel)
        coluna_calendario = ttk.Frame(painel, width=260)
        painel.add(coluna_formulario, weight=4)
        painel.add(coluna_calendario, weight=0)

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
            self._combo_selecao_cliente["values"] = rotulos

    def _marcar_combo_cliente_atual(self, documento: dict[str, Any]) -> None:
        """Seleciona no combo o item correspondente ao documento carregado."""
        chave = documento.get("chave") or {}
        c = str(chave.get(CHAVE_JSON_CONTRATANTE, "")).strip()
        n = str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
        rotulo = f"{c} — {n}" if c and n else (c or n)
        if self._combo_selecao_cliente and rotulo in self._combo_selecao_cliente["values"]:
            self._combo_selecao_cliente.set(rotulo)

    def _ao_trocar_cliente_combo(self, _evento: tk.Event | None = None) -> None:
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
        topo = tk.Toplevel(self)
        topo.title("Novo cliente")
        topo.transient(self)
        topo.grab_set()
        ttk.Label(topo, text="Contratante (chave):").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        entrada_contratante = ttk.Entry(topo, width=48)
        entrada_contratante.grid(row=0, column=1, padx=8, pady=6)
        ttk.Label(topo, text="Natureza do serviço (chave):").grid(
            row=1, column=0, sticky=tk.W, padx=8, pady=6
        )
        entrada_natureza = ttk.Entry(topo, width=48)
        entrada_natureza.grid(row=1, column=1, padx=8, pady=6)

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

        ttk.Button(topo, text="Criar e abrir", command=confirmar).grid(
            row=2, column=0, columnspan=2, pady=12
        )

    def _carregar_cabecalho_no_formulario(self) -> None:
        """Copia `cabecalho_fixo` do documento para os campos da primeira aba."""
        if not self._documento_atual:
            return
        cabecalho = self._documento_atual.get("cabecalho_fixo") or {}
        for campo, widget in self._widgets_cabecalho.items():
            widget.delete(0, tk.END)
            widget.insert(0, str(cabecalho.get(campo, "") or ""))

    def _copiar_cabecalho_formulario_para_documento(self) -> None:
        """Grava no documento em memória os valores atuais dos campos do cabeçalho."""
        if not self._documento_atual:
            return
        cabecalho = dict(self._documento_atual.get("cabecalho_fixo") or {})
        for campo, widget in self._widgets_cabecalho.items():
            cabecalho[campo] = widget.get().strip()
        self._documento_atual["cabecalho_fixo"] = cabecalho

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

        for campo, widget in self._widgets_cabecalho.items():
            valor = str(modelo.get(campo, "") or "")
            widget.delete(0, tk.END)
            widget.insert(0, valor)

        if self._documento_atual:
            self._documento_atual["cabecalho_fixo"] = dict(modelo)

        messagebox.showinfo(
            "Modelo de cabeçalho",
            "Modelo de cabeçalho carregado com sucesso!",
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
    PASTA_DADOS_RDO.mkdir(parents=True, exist_ok=True)
    garantir_arquivo_config_regras_existe()
    app = AplicacaoRdo()
    app.mainloop()
