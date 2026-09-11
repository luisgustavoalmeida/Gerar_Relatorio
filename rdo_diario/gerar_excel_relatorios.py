"""
Gera ficheiros Excel RDO e FT a partir do JSON do cliente e do mapa de células.

Um ficheiro RDO por mês (uma folha por dia com registo). Um ficheiro FT por mês.
Os modelos são copiados de `template/`; o mapa editável está em `template/mapa_celulas_excel.json`.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

from rdo_diario.assinaturas import resolver_assinatura
from rdo_diario.calculo_metricas_horas import calcular_metricas_horas_para_dia
from rdo_diario.config_horas import carregar_config_regras_horas
from rdo_diario.horario_util import horarios_ponto_com_deslocamento_para_ft
from rdo_diario.logos import resolver_logo
from rdo_diario.paths import (
    ARQUIVO_MAPA_CELULAS_EXCEL_JSON,
    PASTA_SAIDA_RELATORIOS_EXCEL,
    RAIZ_PROJETO,
)
from rdo_diario.schema import (
    CHAVE_JSON_ASSINATURA_ARQUIVO,
    CHAVE_JSON_FOLHA_RELATORIO_MES,
    CHAVE_JSON_LOGO_ARQUIVO,
    CHAVE_JSON_NUMERO_RELATORIO_MES,
    extrair_horarios_do_registro_dia,
    incluir_deslocamento_nas_horas,
    mapa_numero_folha_por_mes,
    registro_de_dia_possui_conteudo,
)


def _resolver_caminho_relativo_raiz(rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else (RAIZ_PROJETO / p)


def _carregar_mapa_celulas(caminho: Path | None = None) -> dict[str, Any]:
    alvo = caminho or ARQUIVO_MAPA_CELULAS_EXCEL_JSON
    with alvo.open(encoding="utf-8") as f:
        return json.load(f)


def _slug_seguro(texto: str) -> str:
    t = re.sub(r'[<>:"/\\|?*]+', "_", (texto or "").strip())
    t = re.sub(r"\s+", "_", t)
    return t or "sem_nome"


def _nome_arquivo_relatorio_mes(
    documento: dict[str, Any],
    ano: int,
    mes: int,
    tipo: str,
) -> str:
    """
    Nome do Excel mensal: data, tipo (RDO/FT), natureza do serviço e funcionário.

    Exemplo: ``2026-05_RDO_Supervisorio_UHE_Rondon_Luis_Gustavo_de_Almeida.xlsx``
    """
    cab = documento.get("cabecalho_fixo") or {}
    chave = documento.get("chave") or {}
    partes = [f"{ano:04d}-{mes:02d}", tipo]
    for texto in (
        str(cab.get("natureza_servico") or chave.get("natureza_servico") or ""),
        str(cab.get("nome_funcionario") or ""),
    ):
        slug = _slug_seguro(texto)
        if slug != "sem_nome":
            partes.append(slug)
    nome_base = "_".join(partes)
    if len(nome_base) > 240:
        nome_base = nome_base[:240].rstrip("_")
    return f"{nome_base}.xlsx"


def _caminho_pasta_saida_cliente(documento: dict[str, Any], base: Path | None = None) -> Path:
    """Caminho da pasta de saída Excel do cliente (sem criar pastas)."""
    chave = documento.get("chave") or {}
    c = str(chave.get("contratante") or "").strip()
    n = str(chave.get("natureza_servico") or "").strip()
    raiz = base if base is not None else PASTA_SAIDA_RELATORIOS_EXCEL
    return raiz / _slug_seguro(c) / _slug_seguro(n)


def _pasta_cliente_saida(documento: dict[str, Any], base: Path | None = None) -> Path:
    pasta = _caminho_pasta_saida_cliente(documento, base)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def remover_saida_relatorios_excel_cliente(documento: dict[str, Any]) -> None:
    """Apaga a pasta de relatórios Excel gerados para o cliente (se existir)."""
    pasta = _caminho_pasta_saida_cliente(documento)
    if pasta.is_dir():
        shutil.rmtree(pasta)
    pasta_contratante = pasta.parent
    if (
        pasta_contratante.is_dir()
        and pasta_contratante != PASTA_SAIDA_RELATORIOS_EXCEL
        and not any(pasta_contratante.iterdir())
    ):
        pasta_contratante.rmdir()


def _hhmm_para_time(texto: str) -> time | None:
    t = (texto or "").strip()
    if not t:
        return None
    t = t.replace(".", ":")
    partes = t.split(":")
    try:
        h = int(partes[0])
        m = int(partes[1]) if len(partes) > 1 else 0
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return time(h, m)
    except (ValueError, IndexError):
        return None


def _hhmm_para_timedelta(texto: str) -> timedelta | None:
    t = (texto or "").strip()
    if not t:
        return None
    t = t.replace(".", ":")
    partes = t.split(":")
    try:
        h = int(partes[0])
        m = int(partes[1]) if len(partes) > 1 else 0
        if h < 0 or m < 0 or m > 59:
            return None
        return timedelta(hours=h, minutes=m)
    except (ValueError, IndexError):
        return None


def _texto_horarios_ponto(registro: dict[str, Any]) -> str:
    h = extrair_horarios_do_registro_dia(registro)
    rotulos = (
        ("Entrada", "ponto_entrada"),
        ("Saída almoço", "ponto_saida_almoco"),
        ("Entrada almoço", "ponto_entrada_almoco"),
        ("Saída", "ponto_saida"),
        ("Desloc. ida", "deslocamento_ida"),
        ("Desloc. volta", "deslocamento_volta"),
    )
    partes: list[str] = []
    for rot, ch in rotulos:
        v = str(h.get(ch, "") or "").strip()
        if v:
            partes.append(f"{rot}: {v}")
    return " | ".join(partes)


def _valor_metrica_aninhada(registro: dict[str, Any], caminho: str) -> Any:
    partes = caminho.split(".")
    cur: Any = registro
    for p in partes:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def _extrair_primeira_linha(texto: str) -> str:
    """Extrai apenas a primeira linha do texto."""
    linhas = str(texto or "").splitlines()
    return linhas[0] if linhas else ""


def _concatenar_registros_primeira_linha(registro: dict[str, Any]) -> str:
    """Concatena a primeira linha dos campos de registro (servico, extra_escopo, ociosidade)."""
    textos: list[str] = []
    for campo in ("registro_servico", "registro_extra_escopo", "registro_ociosidade"):
        valor = str(registro.get(campo) or "")
        primeira_linha = _extrair_primeira_linha(valor)
        if primeira_linha:
            textos.append(primeira_linha)
    return " ".join(textos).strip()


def _escrever_celula(ws: Any, endereco: str, valor: Any, wrap: bool = False) -> None:
    if not endereco:
        return
    c = ws[endereco]
    c.value = valor
    if wrap:
        al = c.alignment.copy() if c.alignment else Alignment()
        c.alignment = Alignment(
            horizontal=al.horizontal,
            vertical=al.vertical or "top",
            wrap_text=True,
        )


def _datas_registros_por_mes(registros: dict[str, Any]) -> dict[tuple[int, int], list[str]]:
    por_mes: dict[tuple[int, int], list[str]] = {}
    for iso, registro in registros.items():
        if not isinstance(registro, dict):
            continue
        if not registro_de_dia_possui_conteudo(registro):
            continue
        try:
            d = date.fromisoformat(str(iso).strip()[:10])
        except ValueError:
            continue
        chave_mes = (d.year, d.month)
        por_mes.setdefault(chave_mes, []).append(str(iso).strip()[:10])
    for ch in por_mes:
        por_mes[ch].sort()
    return por_mes


def _titulo_planilha_dia(iso_data: str) -> str:
    """Nome de folha Excel (máx. 31 caracteres, sem : * ? / \\ [ ])."""
    t = iso_data[:31]
    for a, b in (("/", "-"), (":", "-"), ("\\", "-"), ("?", ""), ("*", ""), ("[", ""), ("]", "")):
        t = t.replace(a, b)
    return t or "Dia"


def _col_width_px(ws, col_letter: str) -> float:
    dim = ws.column_dimensions.get(col_letter)
    width = dim.width if dim is not None and dim.width is not None else None
    if width is None:
        width = ws.sheet_format.defaultColWidth or 8.43
    return float(width) * 7.0 + 5.0


def _row_height_px(ws, row: int) -> float:
    dim = ws.row_dimensions.get(row)
    height = dim.height if dim is not None and dim.height is not None else None
    if height is None:
        height = ws.sheet_format.defaultRowHeight or 15.0
    return float(height) * (96.0 / 72.0)


def _intervalo_tamanho_px(ws, inicio: str, fim: str) -> tuple[int, int]:
    c1, r1 = coordinate_from_string(inicio.upper())
    c2, r2 = coordinate_from_string(fim.upper())
    i1 = column_index_from_string(c1)
    i2 = column_index_from_string(c2)
    if i2 < i1:
        i1, i2 = i2, i1
    if r2 < r1:
        r1, r2 = r2, r1
    largura = sum(_col_width_px(ws, get_column_letter(i)) for i in range(i1, i2 + 1))
    altura = sum(_row_height_px(ws, r) for r in range(int(r1), int(r2) + 1))
    return max(1, int(round(largura))), max(1, int(round(altura)))


def _aparar_assinatura(pil_img):
    """Remove margem transparente / fundo branco para a tinta preencher melhor a área."""
    img = pil_img.convert("RGBA")
    w, h = img.size
    pixels = img.load()
    min_x, min_y, max_x, max_y = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a < 20:
                continue
            if r >= 248 and g >= 248 and b >= 248:
                continue
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y
    if max_x < min_x or max_y < min_y:
        return img
    pad = 3
    return img.crop(
        (
            max(0, min_x - pad),
            max(0, min_y - pad),
            min(w, max_x + 1 + pad),
            min(h, max_y + 1 + pad),
        )
    )


def _anchor_marker(celula: str, *, col_off_px: int = 0, row_off_px: int = 0):
    from openpyxl.drawing.spreadsheet_drawing import AnchorMarker
    from openpyxl.utils.units import pixels_to_EMU

    col_letters, row = coordinate_from_string(celula.upper())
    col = column_index_from_string(col_letters) - 1
    row_idx = int(row) - 1
    return AnchorMarker(
        col=col,
        colOff=pixels_to_EMU(max(0, col_off_px)),
        row=row_idx,
        rowOff=pixels_to_EMU(max(0, row_off_px)),
    )


def _cfg_assinatura_tipo(mapa: dict[str, Any], tipo: str) -> dict[str, Any]:
    """Configuração de assinatura para «rdo» ou «ft» (com defaults)."""
    bloco = mapa.get("assinatura") or {}
    defaults_rdo = {
        "celula_inicio": "G74",
        "celula_fim": "H76",
        "alinhamento_horizontal": "esquerda",
        "alinhamento_vertical": "base",
        "margem_base_px": 0,
        "offset_x_px": 2,
        "fator_preenchimento": 0.72,
        "aparar_margens": True,
    }
    defaults_ft = {
        "celula_inicio": "C45",
        "celula_fim": "D48",
        "alinhamento_horizontal": "centro",
        "alinhamento_vertical": "base",
        "margem_base_px": 0,
        "offset_x_px": 0,
        "fator_preenchimento": 0.85,
        "aparar_margens": True,
    }
    if isinstance(bloco.get(tipo), dict):
        base = defaults_rdo if tipo == "rdo" else defaults_ft
        return {**base, **bloco[tipo]}
    return defaults_rdo if tipo == "rdo" else defaults_ft


def _cfg_logo_rdo(mapa: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "celula_inicio": "C1",
        "celula_fim": "C5",
        "alinhamento_horizontal": "centro",
        "alinhamento_vertical": "centro",
        "margem_x_px": 4,
        "margem_topo_px": 2,
        "margem_base_px": 2,
        "fator_preenchimento": 0.95,
        "aparar_margens": False,
    }
    bloco = mapa.get("logo") or {}
    if isinstance(bloco.get("rdo"), dict):
        return {**defaults, **bloco["rdo"]}
    if isinstance(bloco, dict) and bloco.get("celula_inicio"):
        return {**defaults, **bloco}
    return defaults


def _inserir_imagem_na_folha(ws, path: Path, cfg: dict[str, Any]) -> None:
    """
    Insere a imagem na área configurada sem distorcer nem alterar alturas de linha.
    Alinhamento horizontal/vertical configurável.

    O bitmap embutido fica com resolução superior ao tamanho de ecrã (≈2×), para
    manter nitidez no Excel; ``width``/``height`` controlam só o tamanho visual.
    """
    import io

    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor
    from openpyxl.drawing.xdr import XDRPositiveSize2D
    from openpyxl.utils.units import pixels_to_EMU
    from PIL import Image as PILImage

    inicio = str(cfg.get("celula_inicio") or "C1").strip().upper() or "C1"
    fim = str(cfg.get("celula_fim") or inicio).strip().upper() or inicio

    box_w, box_h = _intervalo_tamanho_px(ws, inicio, fim)
    margem_x = int(cfg.get("margem_x_px") or 8)
    margem_topo = int(cfg.get("margem_topo_px") or 2)
    margem_base = int(cfg.get("margem_base_px") if cfg.get("margem_base_px") is not None else 3)
    offset_x = int(cfg.get("offset_x_px") or 0)
    offset_y = int(cfg.get("offset_y_px") or 0)
    fator = float(cfg.get("fator_preenchimento") or 1.0)
    fator = max(0.3, min(fator, 1.0))
    aparar = bool(cfg.get("aparar_margens", True))
    util_w = max(1, box_w - 2 * margem_x)
    util_h = max(1, box_h - margem_topo - margem_base)

    try:
        with PILImage.open(path) as raw:
            trabalhada = _aparar_assinatura(raw) if aparar else raw.convert("RGBA")
            escala_display = min(util_w / trabalhada.width, util_h / trabalhada.height) * fator
            dest_w = max(1, int(round(trabalhada.width * escala_display)))
            dest_h = max(1, int(round(trabalhada.height * escala_display)))

            fator_nitidez = 2
            max_bmp_w = dest_w * fator_nitidez
            max_bmp_h = dest_h * fator_nitidez
            if trabalhada.width > max_bmp_w or trabalhada.height > max_bmp_h:
                escala_bmp = min(max_bmp_w / trabalhada.width, max_bmp_h / trabalhada.height)
                bmp_w = max(1, int(round(trabalhada.width * escala_bmp)))
                bmp_h = max(1, int(round(trabalhada.height * escala_bmp)))
                trabalhada = trabalhada.resize((bmp_w, bmp_h), PILImage.Resampling.LANCZOS)

            buf = io.BytesIO()
            trabalhada.save(buf, format="PNG", optimize=True)
            buf.seek(0)
    except OSError:
        return

    try:
        img = XLImage(buf)
    except Exception:
        return
    img.width = dest_w
    img.height = dest_h

    alin_h = str(cfg.get("alinhamento_horizontal") or "centro").strip().lower()
    if alin_h in ("esquerda", "left"):
        off_x = margem_x + offset_x
    elif alin_h in ("direita", "right"):
        off_x = margem_x + max(0, util_w - dest_w) + offset_x
    else:
        off_x = margem_x + max(0, (util_w - dest_w) // 2) + offset_x
    off_x = max(0, off_x)

    alin_v = str(cfg.get("alinhamento_vertical") or "base").strip().lower()
    if alin_v in ("topo", "top"):
        off_y = max(0, margem_topo + offset_y)
    elif alin_v in ("centro", "center", "meio"):
        off_y = max(0, margem_topo + max(0, (util_h - dest_h) // 2) + offset_y)
    else:
        off_y = max(0, box_h - margem_base - dest_h + offset_y)

    img.anchor = OneCellAnchor(
        _from=_anchor_marker(inicio, col_off_px=off_x, row_off_px=off_y),
        ext=XDRPositiveSize2D(pixels_to_EMU(dest_w), pixels_to_EMU(dest_h)),
    )
    ws.add_image(img)


def _inserir_assinatura_na_folha(ws, path: Path, cfg: dict[str, Any]) -> None:
    """Compatibilidade: assinatura usa o inseridor genérico (com aparar margens)."""
    cfg_ass = dict(cfg)
    cfg_ass.setdefault("aparar_margens", True)
    _inserir_imagem_na_folha(ws, path, cfg_ass)


def _inserir_assinatura_documento(ws, documento: dict[str, Any], mapa: dict[str, Any], tipo: str) -> None:
    cab = documento.get("cabecalho_fixo") or {}
    path = resolver_assinatura(
        str(cab.get("nome_funcionario") or ""),
        cab.get(CHAVE_JSON_ASSINATURA_ARQUIVO),
    )
    if not path:
        return
    _inserir_assinatura_na_folha(ws, path, _cfg_assinatura_tipo(mapa, tipo))


def _inserir_logo_documento(ws, documento: dict[str, Any], mapa: dict[str, Any]) -> None:
    cab = documento.get("cabecalho_fixo") or {}
    nome_empresa = str(cab.get("contratada") or cab.get("contratante") or "").strip()
    path = resolver_logo(nome_empresa, cab.get(CHAVE_JSON_LOGO_ARQUIVO))
    if not path:
        return
    _inserir_imagem_na_folha(ws, path, _cfg_logo_rdo(mapa))


def _preencher_rdo_mes(
    documento: dict[str, Any],
    mapa: dict[str, Any],
    ano: int,
    mes: int,
    datas_iso: list[str],
    pasta_saida: Path,
) -> Path:
    cfg = mapa.get("rdo") or {}
    tpl = _resolver_caminho_relativo_raiz(str(cfg.get("arquivo_template") or "template/RDO.xlsx"))
    nome_modelo = str(cfg.get("planilha_modelo") or "")
    if not nome_modelo.strip():
        raise ValueError("mapa: rdo.planilha_modelo em falta.")

    wb = load_workbook(tpl)
    if nome_modelo not in wb.sheetnames:
        raise FileNotFoundError(f"Modelo RDO: folha «{nome_modelo}» não existe em {tpl}.")

    ws_modelo = wb[nome_modelo]
    pares: list[tuple[str, Any]] = []
    for iso in datas_iso:
        dup = wb.copy_worksheet(ws_modelo)
        dup.title = _titulo_planilha_dia(iso)
        pares.append((iso, dup))
    wb.remove(ws_modelo)

    cab = documento.get("cabecalho_fixo") or {}
    registros = documento.get("registros_diarios") or {}
    map_cab = cfg.get("cabecalho_fixo") or {}
    map_dia = cfg.get("por_registro_dia") or {}
    cel_obs = str(cfg.get("observacoes_fiscalizacao_dia") or "").strip()
    cel_hor = str(cfg.get("horarios_ponto_detalhe") or "").strip()
    cel_data_geracao = str(cfg.get("data_geracao_celula") or "").strip()
    folhas_mes = mapa_numero_folha_por_mes(registros, ano, mes)
    data_geracao = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for iso, ws in pares:
        reg = registros.get(iso) or {}
        if not isinstance(reg, dict):
            reg = {}
        posicao_folha = folhas_mes.get(iso)

        for chave_json, endereco in map_cab.items():
            if not endereco:
                continue
            val = cab.get(chave_json)
            if val is None:
                continue
            _escrever_celula(ws, str(endereco), str(val).strip() if val is not None else "")

        for chave_json, endereco in map_dia.items():
            if not endereco:
                continue

            ed = str(endereco)
            if chave_json == "data_relatorio":
                try:
                    d = date.fromisoformat(iso)
                    _escrever_celula(ws, ed, datetime(d.year, d.month, d.day))
                except ValueError:
                    pass
                continue
            if chave_json == CHAVE_JSON_NUMERO_RELATORIO_MES:
                if posicao_folha is not None:
                    _escrever_celula(ws, ed, posicao_folha[0])
                continue
            if chave_json == CHAVE_JSON_FOLHA_RELATORIO_MES:
                if posicao_folha is not None:
                    _escrever_celula(ws, ed, posicao_folha[2])
                continue
            if chave_json in ("registro_servico", "registro_extra_escopo", "registro_ociosidade"):
                txt = str(reg.get(chave_json) or "")
                _escrever_celula(ws, ed, txt, wrap=True)
                continue
            if chave_json in ("tempo_serviço", "tempo_extra_escopo", "tempo_ociosidade"):
                _escrever_celula(ws, ed, str(reg.get(chave_json) or "").strip())
                continue
            if chave_json in ("ponto_entrada", "ponto_saida", "deslocamento_ida", "deslocamento_volta"):
                hor = _hhmm_para_time(str(reg.get(chave_json) or ""))
                if hor is not None:
                    _escrever_celula(ws, ed, hor)
                else:
                    _escrever_celula(ws, ed, str(reg.get(chave_json) or "").strip())
                continue           
            
            val = reg.get(chave_json)
            if val is None:
                continue
            _escrever_celula(ws, ed, str(val) if val is not None else "")

        if cel_obs:
            _escrever_celula(ws, cel_obs, str(cab.get("fiscalizacao") or "").strip(), wrap=True)
        if cel_hor:
            _escrever_celula(ws, cel_hor, _texto_horarios_ponto(reg), wrap=True)
        if cel_data_geracao:
            _escrever_celula(ws, cel_data_geracao, data_geracao)
            cel = ws[cel_data_geracao]
            cel.number_format = "DD/MM/YYYY"
            al = cel.alignment.copy() if cel.alignment else Alignment()
            cel.alignment = Alignment(
                horizontal="left",
                vertical=al.vertical or "center",
                wrap_text=al.wrap_text,
            )

        _inserir_logo_documento(ws, documento, mapa)
        _inserir_assinatura_documento(ws, documento, mapa, "rdo")

    nome_f = _nome_arquivo_relatorio_mes(documento, ano, mes, "RDO")
    destino = pasta_saida / nome_f
    wb.save(destino)
    wb.close()
    return destino


def _preencher_ft_mes(
    documento: dict[str, Any],
    mapa: dict[str, Any],
    ano: int,
    mes: int,
    datas_iso: list[str],
    pasta_saida: Path,
) -> Path:
    cfg = mapa.get("ft") or {}
    tpl = _resolver_caminho_relativo_raiz(str(cfg.get("arquivo_template") or "template/FT.xlsx"))
    folha = str(cfg.get("folha_dados") or "FICHA TEMPO")

    wb = load_workbook(tpl)
    if folha not in wb.sheetnames:
        raise FileNotFoundError(f"Modelo FT: folha «{folha}» não existe em {tpl}.")
    ws = wb[folha]

    cab = documento.get("cabecalho_fixo") or {}
    registros = documento.get("registros_diarios") or {}
    map_cab = cfg.get("cabecalho_fixo") or {}
    colunas = cfg.get("colunas") or {}
    lin_ini = int(cfg.get("primeira_linha_dia") or 10)
    lin_fim = int(cfg.get("ultima_linha_dia") or 40)
    cel_mes = str(cfg.get("data_mes_referencia_celula") or "A8")
    config_horas = carregar_config_regras_horas()

    primeiro = date(ano, mes, 1)
    ws[cel_mes].value = datetime(primeiro.year, primeiro.month, primeiro.day)

    conjunto_iso = set(datas_iso)

    def col_of(key: str) -> str:
        return str(colunas.get(key) or "").strip()

    for linha in range(lin_ini, lin_fim + 1):
        for _k, col in colunas.items():
            if col:
                ws[f"{str(col).strip()}{linha}"].value = None

        dia_mes = linha - lin_ini + 1
        try:
            d = date(ano, mes, dia_mes)
        except ValueError:
            continue

        iso = d.isoformat()
        if iso not in conjunto_iso:
            continue

        reg = registros.get(iso) or {}
        if not isinstance(reg, dict):
            continue
        hor = extrair_horarios_do_registro_dia(reg)
        incluir_desloc = incluir_deslocamento_nas_horas(reg)
        if incluir_desloc:
            hor_ft = horarios_ponto_com_deslocamento_para_ft(
                str(hor.get("ponto_entrada") or ""),
                str(hor.get("ponto_saida_almoco") or ""),
                str(hor.get("ponto_entrada_almoco") or ""),
                str(hor.get("ponto_saida") or ""),
                str(hor.get("deslocamento_ida") or ""),
                str(hor.get("deslocamento_volta") or ""),
            )
        else:
            hor_ft = {
                "ponto_entrada": str(hor.get("ponto_entrada") or ""),
                "ponto_saida_almoco": str(hor.get("ponto_saida_almoco") or ""),
                "ponto_entrada_almoco": str(hor.get("ponto_entrada_almoco") or ""),
                "ponto_saida": str(hor.get("ponto_saida") or ""),
            }
        # Sempre recalcula na exportação (evita métricas JSON desatualizadas).
        metricas_ft = calcular_metricas_horas_para_dia(d, reg, config_horas)

        e, f, g, h = (
            col_of("ponto_entrada"),
            col_of("ponto_saida_almoco"),
            col_of("ponto_entrada_almoco"),
            col_of("ponto_saida"),
        )
        for letra, chave in (
            (e, "ponto_entrada"),
            (f, "ponto_saida_almoco"),
            (g, "ponto_entrada_almoco"),
            (h, "ponto_saida"),
        ):
            if letra:
                bruto = str(hor_ft.get(chave) or "").strip()
                if not bruto:
                    ws[f"{letra}{linha}"].value = None
                    continue
                t = _hhmm_para_time(bruto)
                ws[f"{letra}{linha}"].value = t if t is not None else bruto

        for map_key, chave_metrica in (
            ("metricas_horas.normais_hhmm", "normais_hhmm"),
            ("metricas_horas.extra_50_hhmm", "extra_50_hhmm"),
            ("metricas_horas.extra_100_hhmm", "extra_100_hhmm"),
            ("metricas_horas.adicional_noturno_hhmm", "adicional_noturno_hhmm"),
        ):
            letra = col_of(map_key)
            if not letra:
                continue
            if metricas_ft.get("calculo_valido"):
                txt = metricas_ft.get(chave_metrica)
                td = _hhmm_para_timedelta(str(txt or ""))
                ws[f"{letra}{linha}"].value = td if td is not None else None
            else:
                ws[f"{letra}{linha}"].value = None

        ocol = col_of("registro_servico")
        if ocol:
            texto_concatenado = _concatenar_registros_primeira_linha(reg)
            ws[f"{ocol}{linha}"].value = texto_concatenado or None
            c = ws[f"{ocol}{linha}"]
            al = c.alignment.copy() if c.alignment else Alignment()
            c.alignment = Alignment(
                horizontal=al.horizontal, vertical=al.vertical or "top", wrap_text=True
            )

        wcol = col_of("tipo_dia_feriado_coluna_w")
        if wcol:
            tipo = str(metricas_ft.get("tipo_dia") or "").strip().lower()
            if tipo == "feriado":
                ws[f"{wcol}{linha}"].value = "FERIADO"

    for chave_json, endereco in map_cab.items():
        if not endereco:
            continue
        val = cab.get(chave_json)
        if val is None:
            continue
        _escrever_celula(ws, str(endereco), str(val).strip() if val is not None else "")

    _inserir_assinatura_documento(ws, documento, mapa, "ft")

    nome_f = _nome_arquivo_relatorio_mes(documento, ano, mes, "FT")
    destino = pasta_saida / nome_f
    wb.save(destino)
    wb.close()
    return destino


def gerar_relatorios_excel(
    documento: dict[str, Any],
    caminho_json: Path | None = None,
    mapa: dict[str, Any] | None = None,
    pasta_saida_base: Path | None = None,
    *,
    ano: int | None = None,
    mes: int | None = None,
) -> list[Path]:
    """
    Gera pares RDO/FT por mês com base nos registos diários do documento.

    Args:
        documento: conteúdo do JSON (cabecalho_fixo, registros_diarios, chave).
        caminho_json: opcional, apenas para mensagens de contexto.
        mapa: mapa de células (se None, lê `template/mapa_celulas_excel.json`).
        pasta_saida_base: substitui a pasta base `saida_relatorios` (útil para testes).
        ano, mes: se ambos forem indicados, gera apenas esse mês.

    Returns:
        Lista de ficheiros Excel criados ou sobrescritos.
    """
    _ = caminho_json
    if (ano is None) ^ (mes is None):
        raise ValueError("Indique ano e mês em conjunto, ou omita ambos para gerar todos os meses.")

    m = mapa if mapa is not None else _carregar_mapa_celulas()
    registros = documento.get("registros_diarios") or {}
    if not isinstance(registros, dict) or not registros:
        raise ValueError("Não há registros_diarios no documento.")

    pasta_cliente = _pasta_cliente_saida(documento, pasta_saida_base)

    por_mes = _datas_registros_por_mes(registros)
    if not por_mes:
        raise ValueError("Nenhuma data ISO válida em registros_diarios.")

    if ano is not None and mes is not None:
        chave_mes = (ano, mes)
        if chave_mes not in por_mes:
            raise ValueError(f"Não há registros no mês {mes:02d}/{ano}.")
        por_mes = {chave_mes: por_mes[chave_mes]}

    gerados: list[Path] = []
    for (a, m_mes), datas_iso in sorted(por_mes.items()):
        gerados.append(_preencher_rdo_mes(documento, m, a, m_mes, datas_iso, pasta_cliente))
        gerados.append(_preencher_ft_mes(documento, m, a, m_mes, datas_iso, pasta_cliente))

    return gerados
