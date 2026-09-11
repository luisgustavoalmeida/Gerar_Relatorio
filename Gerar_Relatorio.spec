# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — Gerar Relatório RDO (Windows, onefile).

Gerar executável:
  compilar.bat
  ou: pyinstaller --noconfirm --clean gerar_relatorio.spec
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH)

block_cipher = None

# CustomTkinter e tkcalendar precisam de assets embutidos; openpyxl/holidays só em import.
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")
tkcal_datas, tkcal_binaries, tkcal_hiddenimports = collect_all("tkcalendar")
pil_datas, pil_binaries, pil_hiddenimports = collect_all("PIL")

icon_ctk = None
for candidato in (
    ROOT / "build_resources" / "icone_exe.ico",
    ROOT / ".venv" / "Lib" / "site-packages" / "customtkinter" / "assets" / "icons" / "CustomTkinter_icon_Windows.ico",
    ROOT / "venv" / "Lib" / "site-packages" / "customtkinter" / "assets" / "icons" / "CustomTkinter_icon_Windows.ico",
):
    if candidato.is_file():
        icon_ctk = str(candidato)
        break

if not icon_ctk:
    raise SystemExit(
        "Icone nao encontrado. Execute compilar.bat ou coloque build_resources\\icone_exe.ico"
    )

hiddenimports = (
    ctk_hiddenimports
    + tkcal_hiddenimports
    + pil_hiddenimports
    + [
        "PIL",
        "PIL.Image",
        "PIL.ImageFile",
        "PIL.PngImagePlugin",
        "PIL.JpegImagePlugin",
        "PIL.GifImagePlugin",
        "PIL.BmpImagePlugin",
        "PIL.WebPImagePlugin",
        "holidays",
        "holidays.countries",
        "holidays.countries.brazil",
        "openpyxl",
        "openpyxl.cell",
        "openpyxl.cell._writer",
        "openpyxl.styles",
        "openpyxl.styles.alignment",
        "openpyxl.workbook",
        "openpyxl.worksheet",
        "openpyxl.worksheet.worksheet",
    ]
)

datas = (
    [
        ("saida_relatorios", "saida_relatorios"),
        ("template", "template"),
        ("dados_rdo", "dados_rdo"),
        ("build_resources/icone_exe.ico", "build_resources"),
    ]
    + ctk_datas
    + tkcal_datas
    + pil_datas
)

excludes = [
    "pytest",
    "unittest",
    "test",
    "tests",
    "pip",
    "setuptools",
    "distutils",
    "pyinstaller",
]

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=ctk_binaries + tkcal_binaries + pil_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Gerar_Relatorio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_ctk,
)
