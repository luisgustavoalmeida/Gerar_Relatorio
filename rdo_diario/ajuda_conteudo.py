"""
Carrega e formata os ficheiros JSON de ajuda (manual e sobre) para exibição na interface.
"""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path
from typing import Any

import tkinter as tk


def carregar_documento_ajuda(caminho: Path) -> dict[str, Any]:
    """Lê um JSON de ajuda; levanta FileNotFoundError ou json.JSONDecodeError em caso de erro."""
    bruto = caminho.read_text(encoding="utf-8")
    doc = json.loads(bruto)
    if not isinstance(doc, dict):
        raise ValueError("O ficheiro de ajuda deve ser um objeto JSON.")
    return doc


def _inserir_linha(widget: tk.Text, texto: str, tag: str | None = None) -> None:
    if tag:
        widget.insert(tk.END, texto + "\n", tag)
    else:
        widget.insert(tk.END, texto + "\n")


def preencher_widget_manual(widget: tk.Text, doc: dict[str, Any]) -> None:
    """Insere o manual formatado no widget de texto (com tags)."""
    titulo = str(doc.get("titulo", "Manual")).strip()
    widget.insert(tk.END, titulo + "\n", "titulo_principal")
    subtitulo = str(doc.get("subtitulo", "") or "").strip()
    if subtitulo:
        widget.insert(tk.END, subtitulo + "\n\n", "subtitulo")
    for secao in doc.get("secoes") or []:
        if not isinstance(secao, dict):
            continue
        titulo_sec = str(secao.get("titulo", "") or "").strip()
        if titulo_sec:
            widget.insert(tk.END, "\n" + titulo_sec + "\n", "titulo_secao")
        for paragrafo in secao.get("paragrafos") or []:
            if str(paragrafo).strip():
                _inserir_linha(widget, str(paragrafo).strip())
        for item in secao.get("lista") or []:
            if str(item).strip():
                widget.insert(tk.END, "  • " + str(item).strip() + "\n", "lista")
        tabela = secao.get("tabela")
        if isinstance(tabela, list) and tabela:
            widget.insert(tk.END, "\n")
            for linha in tabela:
                if not isinstance(linha, dict):
                    continue
                rotulo = str(linha.get("rotulo", "") or "").strip()
                texto = str(linha.get("texto", "") or "").strip()
                if rotulo:
                    widget.insert(tk.END, f"  {rotulo}: ", "rotulo_tabela")
                if texto:
                    widget.insert(tk.END, texto + "\n")
            widget.insert(tk.END, "\n")


def _inserir_campo_sobre(
    widget: tk.Text,
    rotulo: str,
    valor: Any,
    *,
    tag_valor: str | None = None,
) -> None:
    texto = str(valor or "").strip()
    if not texto:
        return
    widget.insert(tk.END, f"{rotulo}: ", "rotulo_campo")
    if tag_valor:
        widget.insert(tk.END, texto + "\n", tag_valor)
    else:
        widget.insert(tk.END, texto + "\n")


def _inserir_lista_bullet(widget: tk.Text, itens: Any) -> None:
    if not isinstance(itens, list):
        return
    for item in itens:
        if str(item).strip():
            widget.insert(tk.END, "  • " + str(item).strip() + "\n", "lista")


def _inserir_campos_dict(
    widget: tk.Text,
    titulo_secao: str,
    dados: dict[str, Any],
    campos: tuple[tuple[str, str, bool], ...],
) -> None:
    """Renderiza uma secção com campos na ordem definida; o terceiro elemento indica URL."""
    if not isinstance(dados, dict):
        return
    linhas = 0
    vistos: set[str] = set()
    for chave, rotulo, eh_url in campos:
        valor = dados.get(chave)
        if chave == "url" and not str(valor or "").strip():
            valor = dados.get("repositorio_github")
        texto_valor = str(valor or "").strip()
        if not texto_valor:
            continue
        chave_dedup = f"{rotulo}:{texto_valor.lower()}"
        if chave_dedup in vistos:
            continue
        vistos.add(chave_dedup)
        valor = texto_valor
        if linhas == 0:
            widget.insert(tk.END, "\n" + titulo_secao + "\n", "titulo_secao")
        _inserir_campo_sobre(widget, rotulo, valor, tag_valor="url" if eh_url else None)
        linhas += 1


def preencher_widget_sobre(widget: tk.Text, doc: dict[str, Any]) -> None:
    """Insere a informação «Sobre» formatada no widget de texto."""
    titulo = str(doc.get("titulo", "Sobre")).strip()
    widget.insert(tk.END, titulo + "\n", "titulo_principal")
    subtitulo = str(doc.get("subtitulo", "") or "").strip()
    if subtitulo:
        widget.insert(tk.END, subtitulo + "\n\n", "subtitulo")
    else:
        widget.insert(tk.END, "\n")

    _inserir_campos_dict(
        widget,
        "Aplicação",
        doc.get("aplicacao") or {},
        (
            ("nome", "Nome", False),
            ("nome_completo", "Nome completo", False),
            ("versao", "Versão", False),
            ("data_versao", "Data desta versão", False),
            ("versao_formato_dados", "Formato dos dados (JSON)", False),
            ("descricao", "Descrição", False),
            ("data_lancamento", "Data de lançamento", False),
            ("ultima_atualizacao", "Última atualização", False),
            ("plataforma", "Plataforma", False),
            ("python_minimo", "Python mínimo", False),
            ("licenca", "Licença", False),
        ),
    )

    _inserir_campos_dict(
        widget,
        "Criador",
        doc.get("criador") or {},
        (
            ("nome", "Nome", False),
            ("papel", "Função", False),
            ("organizacao", "Organização", False),
            ("email_profissional", "E-mail profissional", False),
            ("email_pessoal", "E-mail pessoal", False),
            ("linkedin", "LinkedIn", True),
            ("discord", "Discord", False),
        ),
    )

    _inserir_campos_dict(
        widget,
        "Repositório",
        doc.get("repositorio") or {},
        (
            ("nome", "Projeto", False),
            ("url", "GitHub", True),
            ("licenca", "Licença", False),
            ("documentacao", "Documentação", False),
        ),
    )

    _inserir_campos_dict(
        widget,
        "Doação",
        doc.get("doacao") or {},
        (
            ("mensagem", "Mensagem", False),
            ("chave_pix", "Chave PIX", False),
        ),
    )

    funcionalidades = doc.get("funcionalidades")
    if isinstance(funcionalidades, list) and funcionalidades:
        widget.insert(tk.END, "\nFuncionalidades principais\n", "titulo_secao")
        _inserir_lista_bullet(widget, funcionalidades)

    historico = doc.get("historico_versoes")
    if isinstance(historico, list) and historico:
        widget.insert(tk.END, "\nHistórico de versões\n", "titulo_secao")
        for entrada in historico:
            if not isinstance(entrada, dict):
                continue
            ver = str(entrada.get("versao", "") or "").strip()
            data = str(entrada.get("data", "") or "").strip()
            notas = str(entrada.get("notas", "") or "").strip()
            if not ver:
                continue
            linha = f"  • v{ver}"
            if data:
                linha += f" ({data})"
            if notas:
                linha += f" — {notas}"
            widget.insert(tk.END, linha + "\n", "lista")

    requisitos = doc.get("requisitos")
    if isinstance(requisitos, list) and requisitos:
        widget.insert(tk.END, "\nRequisitos\n", "titulo_secao")
        _inserir_lista_bullet(widget, requisitos)

    tecnologias = doc.get("tecnologias")
    if isinstance(tecnologias, list) and tecnologias:
        widget.insert(tk.END, "\nTecnologias\n", "titulo_secao")
        for t in tecnologias:
            if not isinstance(t, dict):
                continue
            nome = str(t.get("nome", "") or "").strip()
            uso = str(t.get("uso", "") or "").strip()
            if nome:
                widget.insert(tk.END, f"  • {nome}", "rotulo_campo")
                if uso:
                    widget.insert(tk.END, f" — {uso}\n")
                else:
                    widget.insert(tk.END, "\n")

    pastas = doc.get("pastas_principais")
    if isinstance(pastas, list) and pastas:
        widget.insert(tk.END, "\nPastas principais\n", "titulo_secao")
        _inserir_lista_bullet(widget, pastas)

    suporte = doc.get("suporte")
    if isinstance(suporte, list) and suporte:
        widget.insert(tk.END, "\nSuporte e ajuda\n", "titulo_secao")
        _inserir_lista_bullet(widget, suporte)

    notas = doc.get("notas")
    if isinstance(notas, list) and notas:
        widget.insert(tk.END, "\nNotas\n", "titulo_secao")
        for item in notas:
            if str(item).strip():
                _inserir_linha(widget, str(item).strip())


def configurar_tags_texto_ajuda(widget: tk.Text) -> None:
    """Define estilos visuais partilhados pelos diálogos Manual e Sobre."""
    widget.tag_configure("titulo_principal", font=("Segoe UI", 14, "bold"), spacing3=8)
    widget.tag_configure("subtitulo", font=("Segoe UI", 10), foreground="#444444")
    widget.tag_configure("titulo_secao", font=("Segoe UI", 11, "bold"), spacing1=10, spacing3=4)
    widget.tag_configure("rotulo_campo", font=("Segoe UI", 10, "bold"))
    widget.tag_configure("rotulo_tabela", font=("Segoe UI", 10, "bold"))
    widget.tag_configure("lista", lmargin1=24, lmargin2=36)
    widget.tag_configure("url", foreground="#0645ad", underline=True)
    configurar_links_clicaveis(widget)


def configurar_links_clicaveis(widget: tk.Text) -> None:
    """Abre URLs marcadas com a tag «url» no browser ao clicar (ex.: LinkedIn, GitHub)."""

    def _url_no_clique(event: tk.Event) -> str:
        texto = event.widget
        if not isinstance(texto, tk.Text):
            return "break"
        estava_desativado = str(texto.cget("state")) == str(tk.DISABLED)
        if estava_desativado:
            texto.configure(state=tk.NORMAL)
        try:
            indice = texto.index(f"@{event.x},{event.y}")
        except tk.TclError:
            if estava_desativado:
                texto.configure(state=tk.DISABLED)
            return "break"
        if "url" not in texto.tag_names(indice):
            if estava_desativado:
                texto.configure(state=tk.DISABLED)
            return "break"
        url = ""
        ranges = texto.tag_ranges("url")
        for i in range(0, len(ranges), 2):
            inicio = ranges[i]
            fim = ranges[i + 1]
            if texto.compare(inicio, "<=", indice) and texto.compare(indice, "<", fim):
                url = texto.get(inicio, fim).strip()
                break
        if estava_desativado:
            texto.configure(state=tk.DISABLED)
        if url:
            webbrowser.open(url)
        return "break"

    def _cursor_mao(event: tk.Event) -> str:
        event.widget.configure(cursor="hand2")
        return "break"

    def _cursor_normal(event: tk.Event) -> str:
        event.widget.configure(cursor="")
        return "break"

    widget.tag_bind("url", "<Button-1>", _url_no_clique)
    widget.tag_bind("url", "<Enter>", _cursor_mao)
    widget.tag_bind("url", "<Leave>", _cursor_normal)
