"""Gera icone_exe.ico com vários tamanhos (Explorer / PyInstaller)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESTINO = Path(__file__).resolve().parent / "icone_exe.ico"


def _origem_customtkinter() -> Path:
    import customtkinter

    origem = (
        Path(customtkinter.__file__).resolve().parent
        / "assets"
        / "icons"
        / "CustomTkinter_icon_Windows.ico"
    )
    if not origem.is_file():
        raise FileNotFoundError(f"Icone CustomTkinter nao encontrado: {origem}")
    return origem


def main() -> int:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    origem = _origem_customtkinter()
    try:
        from PIL import Image

        imagem = Image.open(origem).convert("RGBA")
        tamanhos = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        imagem.save(DESTINO, format="ICO", sizes=tamanhos)
    except ImportError:
        shutil.copy2(origem, DESTINO)
        print(
            "Aviso: Pillow nao instalado; icone copiado sem multiplos tamanhos.",
            file=sys.stderr,
        )
    print(DESTINO.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
