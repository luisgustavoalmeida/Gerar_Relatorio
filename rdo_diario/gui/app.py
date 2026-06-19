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
    capturar_geometria_janela_para_salvar,
    carregar_geometria_janela_salva,
    carregar_aba_ativa_salva,
    aplicar_geometria_janela_tela,
    resolver_geometria_janela_inicial,
    salvar_geometria_janela,
    salvar_aba_ativa,
    alternar_tema,
    inicializar_tema,
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
    arquivar_projeto,
    atualizar_chave_cliente,
    carregar_documento_json,
    carregar_ou_criar_cliente,
    desarquivar_projeto,
    encontrar_cliente_por_chave,
    excluir_cliente_do_disco,
    listar_clientes_salvos,
    listar_projetos_arquivados,
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
        self.minsize(LARGURA_JANELA, ALTURA_JANELA)

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
        self._rotulo_metricas_totais = None
        self._barra_cliente: ctk.CTkFrame | None = None
        self._rotulo_barra_cliente: ctk.CTkLabel | None = None
        self._tabview: ctk.CTkTabview | None = None
        self._id_agendamento_salvar_geometria: str | None = None
        self._persistencia_geometria_ativa = False
        self._ultima_geometria_salva: str | None = carregar_geometria_janela_salva()
        self._ultima_aba_salva: str | None = carregar_aba_ativa_salva()

        self._montar_barra_menu()
        self._montar_barra_cliente()
        self._comando_validacao_entrada_hora = self.register(
            lambda proposta: texto_horario_permitido_na_digitacao(proposta)
        )
        self._comando_validacao_entrada_duracao = self.register(
            lambda proposta: texto_duracao_permitido_na_digitacao(proposta)
        )
        self._montar_corpo_janela()
        self._aplicar_geometria_inicial_janela()

        self.bind("<Configure>", self._agendar_salvamento_geometria_janela, add="+")
        self.bind("<ButtonRelease-1>", self._agendar_salvamento_geometria_janela, add="+")
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
        if self._rotulo_metricas_totais is not None:
            self._rotulo_metricas_totais.configure(font=FONT_METRICAS, text_color=COR_TEXTO)
        if self._widget_calendario:
            from rdo_diario.gui.calendario import aplicar_cores_tema_calendario

            aplicar_cores_tema_calendario(self._widget_calendario)
            self._atualizar_marcadores_calendario()
        if self._tabview is not None:
            self._tabview.configure(**opcoes_tabview_ctk())
            configurar_abas_tabview(self._tabview)

    def _alternar_tema_aplicacao(self) -> None:
        alternar_tema()
        forcar_redesenho_tema(self)

    def _montar_barra_cliente(self) -> None:
        """Barra superior: seleção de projeto (contratante + natureza)."""
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
            text="Projeto (contratante + natureza):",
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
        self._tabview = ctk.CTkTabview(
            self,
            command=self._ao_trocar_aba_principal,
            **opcoes_tabview_ctk(),
        )
        self._tabview.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._tabview.add("Cabeçalhos")
        self._tabview.add("Relatórios de trabalho")
        configurar_abas_tabview(self._tabview)
        aba_salva = carregar_aba_ativa_salva()
        if aba_salva:
            self._tabview.set(aba_salva)
        aba_atual = self._tabview.get()
        if aba_atual:
            self._ultima_aba_salva = aba_atual
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
        self._abrir_dialogo_chave_cliente(editar=False)

    def _abrir_dialogo_editar_chave_cliente(self) -> None:
        """Diálogo para alterar a chave do projeto aberto (contratante + natureza)."""
        self._abrir_dialogo_chave_cliente(editar=True)

    def _abrir_dialogo_chave_cliente(self, *, editar: bool) -> None:
        """Formulário partilhado para criar ou editar a chave contratante + natureza."""
        if editar:
            if not self._documento_atual or not self._caminho_arquivo_atual:
                messagebox.showwarning(
                    "Editar chave",
                    "Não há cliente aberto.\n\nSelecione ou crie um cliente primeiro.",
                    parent=self,
                )
                return
            chave = self._documento_atual.get("chave") or {}
            valor_c_inicial = str(chave.get(CHAVE_JSON_CONTRATANTE, "")).strip()
            valor_n_inicial = str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
            ignorar_caminho = self._caminho_arquivo_atual
            titulo_janela = "Editar chave do cliente"
            texto_botao = "Guardar"
        else:
            valor_c_inicial = ""
            valor_n_inicial = ""
            ignorar_caminho = None
            titulo_janela = "Novo cliente"
            texto_botao = "Criar e abrir"

        topo = ctk.CTkToplevel(self)
        topo.title(titulo_janela)
        topo.transient(self)
        topo.grab_set()
        topo.geometry("520x240" if editar else "520x200")

        linha = 0
        if editar:
            ctk.CTkLabel(
                topo,
                text="A chave identifica o ficheiro JSON e a lista «Projeto (contratante + natureza)».",
                wraplength=480,
                justify="left",
                text_color=COR_TEXTO_SECUNDARIO,
            ).grid(row=linha, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 4))
            linha += 1

        ctk.CTkLabel(topo, text="Contratante (chave):").grid(
            row=linha, column=0, sticky="w", padx=12, pady=8
        )
        entrada_contratante = ctk.CTkEntry(topo, width=320)
        entrada_contratante.grid(row=linha, column=1, padx=12, pady=8)
        if valor_c_inicial:
            entrada_contratante.insert(0, valor_c_inicial)
        linha += 1

        ctk.CTkLabel(topo, text="Natureza do serviço (chave):").grid(
            row=linha, column=0, sticky="w", padx=12, pady=8
        )
        entrada_natureza = ctk.CTkEntry(topo, width=320)
        entrada_natureza.grid(row=linha, column=1, padx=12, pady=8)
        if valor_n_inicial:
            entrada_natureza.insert(0, valor_n_inicial)
        linha += 1

        def confirmar() -> None:
            c = entrada_contratante.get().strip()
            n = entrada_natureza.get().strip()
            if not c or not n:
                messagebox.showwarning(
                    "Validação",
                    "Preencha contratante e natureza do serviço.",
                    parent=topo,
                )
                return

            if editar and c == valor_c_inicial and n == valor_n_inicial:
                topo.destroy()
                return

            duplicado = encontrar_cliente_por_chave(c, n, ignorar_caminho=ignorar_caminho)
            if duplicado is not None:
                messagebox.showwarning(
                    "Chave já utilizada",
                    "Já existe um cliente com contratante e natureza do serviço iguais:\n\n"
                    f"{c} — {n}\n\n"
                    f"Ficheiro: {duplicado.name}",
                    parent=topo,
                )
                return

            self._persistir_dia_atual_no_documento()
            if editar:
                self._copiar_cabecalho_formulario_para_documento()
                try:
                    documento, caminho = atualizar_chave_cliente(
                        self._documento_atual,
                        self._caminho_arquivo_atual,
                        c,
                        n,
                    )
                except (OSError, ValueError) as erro:
                    messagebox.showerror("Editar chave", str(erro), parent=topo)
                    return
            else:
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

        ctk.CTkButton(topo, text=texto_botao, command=confirmar).grid(
            row=linha, column=0, columnspan=2, pady=16
        )

    @staticmethod
    def _rotulo_projeto(contratante: str, natureza: str, caminho: Path) -> str:
        if contratante and natureza:
            return f"{contratante} — {natureza}"
        return contratante or natureza or caminho.name

    def _criar_dialogo_selecionar_projeto(
        self,
        *,
        titulo: str,
        dica: str,
        itens: list[tuple[str, str, Path]],
    ) -> tuple[ctk.CTkToplevel, ctk.CTkComboBox, dict[str, Path]]:
        topo = ctk.CTkToplevel(self)
        topo.title(titulo)
        topo.transient(self)
        topo.grab_set()
        topo.geometry("560x200")

        ctk.CTkLabel(
            topo,
            text=dica,
            wraplength=520,
            justify="left",
            text_color=COR_TEXTO_SECUNDARIO,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8))

        ctk.CTkLabel(topo, text="Projecto:").grid(row=1, column=0, sticky="w", padx=12, pady=8)
        mapa_rotulos: dict[str, Path] = {}
        rotulos: list[str] = []
        for contratante, natureza, caminho in itens:
            rotulo = self._rotulo_projeto(contratante, natureza, caminho)
            rotulos.append(rotulo)
            mapa_rotulos[rotulo] = caminho

        combo = ctk.CTkComboBox(topo, values=rotulos, **opcoes_combo_ctk(largura=400))
        combo.grid(row=1, column=1, padx=12, pady=8)
        configurar_combo_ctk_aprimorado(combo)
        if rotulos:
            combo.set(rotulos[0])

        return topo, combo, mapa_rotulos

    def _ativar_proximo_cliente_ou_limpar(self) -> None:
        """Após excluir ou arquivar o projeto aberto: abre outro vigente ou limpa a interface."""
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

    def _abrir_dialogo_arquivar_projeto(self) -> None:
        """Move um projecto vigente para dados_rdo/rdo_arquivados/."""
        itens = listar_clientes_salvos()
        if not itens:
            messagebox.showinfo(
                "Arquivar projeto",
                "Não há projectos vigentes para arquivar.",
                parent=self,
            )
            return

        topo, combo, mapa = self._criar_dialogo_selecionar_projeto(
            titulo="Arquivar projeto",
            dica=(
                "O ficheiro JSON será movido para dados_rdo/rdo_arquivados/ "
                "e deixará de aparecer na lista «Projeto (contratante + natureza)». "
                "Os relatórios Excel gerados mantêm-se em saida_relatorios/."
            ),
            itens=itens,
        )

        def confirmar() -> None:
            caminho = mapa.get(combo.get().strip())
            if caminho is None:
                return
            contratante = ""
            natureza = ""
            for c, n, p in itens:
                if p.resolve() == caminho.resolve():
                    contratante, natureza = c, n
                    break
            rotulo = self._rotulo_projeto(contratante, natureza, caminho)
            if not messagebox.askyesno(
                "Arquivar projeto",
                f"Arquivar o projecto:\n\n{rotulo}\n\n"
                "Poderá restaurá-lo depois em Arquivo → Desarquivar projeto.",
                parent=topo,
                icon="question",
            ):
                return

            era_aberto = (
                self._caminho_arquivo_atual is not None
                and self._caminho_arquivo_atual.resolve() == caminho.resolve()
            )
            if era_aberto:
                self._persistir_dia_atual_no_documento()
                self._salvar_documento_agora(silencioso=True)

            try:
                arquivar_projeto(caminho, contratante=contratante, natureza_servico=natureza)
            except OSError as erro:
                messagebox.showerror("Arquivar projeto", str(erro), parent=topo)
                return

            if era_aberto:
                self._ativar_proximo_cliente_ou_limpar()
            else:
                self._atualizar_lista_combo_clientes()

            messagebox.showinfo(
                "Arquivar projeto",
                f"Projecto arquivado:\n\n{rotulo}",
                parent=self,
            )
            topo.destroy()

        ctk.CTkButton(topo, text="Arquivar", command=confirmar).grid(
            row=2, column=0, columnspan=2, pady=16
        )

    def _abrir_dialogo_desarquivar_projeto(self) -> None:
        """Restaura um projecto de dados_rdo/rdo_arquivados/ para dados_rdo/."""
        itens = listar_projetos_arquivados()
        if not itens:
            messagebox.showinfo(
                "Desarquivar projeto",
                "Não há projectos arquivados em dados_rdo/rdo_arquivados/.",
                parent=self,
            )
            return

        topo, combo, mapa = self._criar_dialogo_selecionar_projeto(
            titulo="Desarquivar projeto",
            dica=(
                "O ficheiro JSON voltará para dados_rdo/ e passará a aparecer "
                "na lista de clientes vigentes."
            ),
            itens=itens,
        )

        def confirmar() -> None:
            caminho = mapa.get(combo.get().strip())
            if caminho is None:
                return
            contratante = ""
            natureza = ""
            for c, n, p in itens:
                if p.resolve() == caminho.resolve():
                    contratante, natureza = c, n
                    break
            rotulo = self._rotulo_projeto(contratante, natureza, caminho)
            if not messagebox.askyesno(
                "Desarquivar projeto",
                f"Desarquivar o projecto:\n\n{rotulo}",
                parent=topo,
                icon="question",
            ):
                return

            try:
                destino = desarquivar_projeto(caminho)
            except OSError as erro:
                messagebox.showerror("Desarquivar projeto", str(erro), parent=topo)
                return

            documento = carregar_documento_json(destino)
            self._documento_atual = documento
            self._caminho_arquivo_atual = destino
            chave = documento.get("chave") or {}
            salvar_memoria_ultimo_cliente(
                str(chave.get(CHAVE_JSON_CONTRATANTE, "")),
                str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")),
            )
            self._atualizar_lista_combo_clientes()
            self._marcar_combo_cliente_atual(documento)
            self._carregar_cabecalho_no_formulario()
            self._carregar_registro_dia_no_formulario(self._data_em_edicao)
            if self._widget_calendario:
                self._widget_calendario.selection_set(self._data_em_edicao)
            self._atualizar_marcadores_calendario()

            messagebox.showinfo(
                "Desarquivar projeto",
                f"Projecto restaurado e aberto:\n\n{rotulo}",
                parent=self,
            )
            topo.destroy()

        ctk.CTkButton(topo, text="Desarquivar e abrir", command=confirmar).grid(
            row=2, column=0, columnspan=2, pady=16
        )

    def _excluir_cliente_atual(self) -> None:
        """Remove o projeto aberto: JSON, relatórios Excel e atualiza a interface."""
        if not self._documento_atual or not self._caminho_arquivo_atual:
            messagebox.showwarning(
                "Excluir projeto",
                "Não há projeto aberto para excluir.\n\n" 
                "Selecione um projeto na lista ou crie um novo.",
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
            "Excluir projeto",
            f"Excluir permanentemente o projeto:\n\n{rotulo}\n\n"
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
            from rdo_diario.gerar_excel_relatorios import remover_saida_relatorios_excel_cliente

            remover_saida_relatorios_excel_cliente(documento_excluido)
            excluir_cliente_do_disco(
                caminho_excluido,
                contratante=contratante,
                natureza_servico=natureza,
            )
        except OSError as erro:
            messagebox.showerror("Excluir projeto", str(erro), parent=self)
            return

        self._ativar_proximo_cliente_ou_limpar()
        self.title("Relatório de atividades diárias")

        messagebox.showinfo(
            "Excluir projeto",
            f"O projeto «{rotulo}» foi excluído.",
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

    def _executar_geracao_excel(
        self,
        *,
        ano: int | None = None,
        mes: int | None = None,
        titulo_dialogo: str = "Gerar Excel",
    ) -> None:
        """Gera ou atualiza ficheiros RDO e FT na pasta `saida_relatorios`."""
        if not self._documento_atual or not self._caminho_arquivo_atual:
            messagebox.showwarning(
                titulo_dialogo,
                "Não há documento carregado. Selecione ou crie um cliente antes de gerar os relatórios.",
            )
            return
        self._persistir_dia_atual_no_documento()
        self._copiar_cabecalho_formulario_para_documento()
        try:
            from rdo_diario.gerar_excel_relatorios import gerar_relatorios_excel

            self._salvar_documento_agora(silencioso=True)
            caminhos = gerar_relatorios_excel(
                self._documento_atual,
                self._caminho_arquivo_atual,
                ano=ano,
                mes=mes,
            )
        except ValueError as e:
            messagebox.showwarning(titulo_dialogo, str(e))
            return
        except OSError as e:
            messagebox.showerror(titulo_dialogo, f"Erro ao gravar ficheiros:\n{e}")
            return
        except Exception as e:
            messagebox.showerror(titulo_dialogo, f"Não foi possível gerar os relatórios:\n{e}")
            return
        linhas = "\n".join(str(p) for p in caminhos)
        messagebox.showinfo(
            titulo_dialogo,
            f"Foram criados ou atualizados {len(caminhos)} ficheiro(s):\n\n{linhas}",
        )

    def _gerar_relatorios_excel_mes_em_edicao(self) -> None:
        """Gera RDO/FT apenas do mês da data selecionada no calendário."""
        ref = self._data_em_edicao
        self._executar_geracao_excel(
            ano=ref.year,
            mes=ref.month,
            titulo_dialogo=f"Gerar Excel — {ref.month:02d}/{ref.year}",
        )

    def _gerar_relatorios_excel_todos_meses(self) -> None:
        """Gera RDO/FT de todos os meses com registos no projeto."""
        self._executar_geracao_excel(titulo_dialogo="Gerar Excel — todos os meses")

    def _aplicar_geometria_inicial_janela(self) -> None:
        """Aplica posição/tamanho após montar a interface (evita layout sobrescrever)."""
        self._persistencia_geometria_ativa = False
        geometria = resolver_geometria_janela_inicial(
            self,
            largura_padrao=LARGURA_JANELA,
            altura_padrao=ALTURA_JANELA,
            geometria_salva=carregar_geometria_janela_salva(),
            largura_minima=LARGURA_JANELA,
            altura_minima=ALTURA_JANELA,
        )
        aplicar_geometria_janela_tela(self, geometria)
        self.update_idletasks()
        self.after(300, self._finalizar_geometria_inicial_janela)

    def _finalizar_geometria_inicial_janela(self) -> None:
        """Define a posição real como referência, sem gravar alterações da abertura."""
        self.update_idletasks()
        geometria_atual = capturar_geometria_janela_para_salvar(self)
        if geometria_atual:
            self._ultima_geometria_salva = geometria_atual
        self._persistencia_geometria_ativa = True

    def _ao_trocar_aba_principal(self) -> None:
        """Grava a aba selecionada para reabrir na próxima execução."""
        if self._tabview is None:
            return
        aba = self._tabview.get()
        if not aba or aba == self._ultima_aba_salva:
            return
        salvar_aba_ativa(aba)
        self._ultima_aba_salva = aba

    def _agendar_salvamento_geometria_janela(self, event: tk.Event) -> None:
        """Grava tamanho e posição após mover ou redimensionar a janela."""
        if event.widget is not self or not self._persistencia_geometria_ativa:
            return
        if self._id_agendamento_salvar_geometria is not None:
            self.after_cancel(self._id_agendamento_salvar_geometria)
        self._id_agendamento_salvar_geometria = self.after(400, self._salvar_geometria_janela_agora)

    def _salvar_geometria_janela_agora(self) -> None:
        self._id_agendamento_salvar_geometria = None
        geometria = capturar_geometria_janela_para_salvar(self)
        if not geometria or geometria == self._ultima_geometria_salva:
            return
        salvar_geometria_janela(geometria)
        self._ultima_geometria_salva = geometria

    def _ao_fechar_janela(self) -> None:
        """Salva em silêncio e encerra a aplicação."""
        try:
            self._salvar_documento_agora(silencioso=True)
        except Exception:
            pass
        if self._id_agendamento_salvar_geometria is not None:
            self.after_cancel(self._id_agendamento_salvar_geometria)
            self._id_agendamento_salvar_geometria = None
            self._salvar_geometria_janela_agora()
        self.destroy()


def iniciar_aplicacao() -> None:
    """Garante a pasta de dados e abre a janela principal."""
    preparar_icone_processo_windows()
    garantir_pastas_executavel()
    inicializar_tema()
    PASTA_DADOS_RDO.mkdir(parents=True, exist_ok=True)
    garantir_arquivo_config_regras_existe()
    app = AplicacaoRdo()
    app.mainloop()
