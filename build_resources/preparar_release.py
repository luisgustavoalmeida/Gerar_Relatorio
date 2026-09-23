"""
Prepara os artefactos da GitHub Release a partir de dist/Gerar_Relatorio.exe.

Gera:
  dist/Gerar_Relatorio_<versão>.zip          — só o .exe (anexo da Release)
  dist/Gerar_Relatorio_<versão>.sha256.txt   — hashes SHA-256 do .exe e do .zip
  dist/RELEASE_v<versão>.md                 — rascunho de notas + checklist de publicação

A versão é lida de template/sobre.json (aplicacao.versao).
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
EXE_NOME = "Gerar_Relatorio.exe"
SOBRE_JSON = ROOT / "template" / "sobre.json"
URL_RELEASES = "https://github.com/luisgustavoalmeida/Gerar_Relatorio/releases/latest"


def _ler_versao() -> tuple[str, str, str]:
    """Devolve (versão, data, notas) a partir de template/sobre.json."""
    if not SOBRE_JSON.is_file():
        raise FileNotFoundError(f"Ficheiro de versão não encontrado: {SOBRE_JSON}")
    doc = json.loads(SOBRE_JSON.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("template/sobre.json deve ser um objeto JSON.")
    app = doc.get("aplicacao") or {}
    if not isinstance(app, dict):
        raise ValueError("Campo «aplicacao» em falta em template/sobre.json.")
    versao = str(app.get("versao") or "").strip()
    if not versao:
        raise ValueError("Campo aplicacao.versao vazio em template/sobre.json.")
    data = str(app.get("data_versao") or app.get("ultima_atualizacao") or "").strip()
    notas = ""
    historico = doc.get("historico_versoes") or []
    if isinstance(historico, list):
        for entrada in historico:
            if not isinstance(entrada, dict):
                continue
            if str(entrada.get("versao") or "").strip() == versao:
                notas = str(entrada.get("notas") or "").strip()
                if not data:
                    data = str(entrada.get("data") or "").strip()
                break
    return versao, data, notas


def _sha256_ficheiro(caminho: Path) -> str:
    digestor = hashlib.sha256()
    with caminho.open("rb") as ficheiro:
        while True:
            bloco = ficheiro.read(1024 * 1024)
            if not bloco:
                break
            digestor.update(bloco)
    return digestor.hexdigest()


def _criar_zip(exe: Path, destino_zip: Path) -> None:
    if destino_zip.is_file():
        destino_zip.unlink()
    with zipfile.ZipFile(destino_zip, "w", compression=zipfile.ZIP_DEFLATED) as arquivo:
        # Só o .exe na raiz do zip — padrão documentado no README.
        arquivo.write(exe, arcname=EXE_NOME)


def _escrever_sha256(destino: Path, pares: list[tuple[Path, str]]) -> None:
    linhas = [f"{digest}  {caminho.name}" for caminho, digest in pares]
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def _escrever_notas_release(
    destino: Path,
    *,
    versao: str,
    data: str,
    notas: str,
    nome_zip: str,
    nome_sha: str,
) -> None:
    tag = f"v{versao}"
    bloco_notas = notas or "(Preencha as notas desta versão em template/sobre.json → historico_versoes.)"
    corpo = f"""# Gerar Relatório {tag}

**Versão:** {versao}  
**Data:** {data or "(definir em template/sobre.json)"}  
**Tag sugerida:** `{tag}`  
**Título sugerido na GitHub Release:** `Gerar Relatório {tag}`

## Notas desta versão

{bloco_notas}

## Instalação (utilizador final)

1. Em [Releases]({URL_RELEASES}), em **Assets**, descarregue **`{nome_zip}`**.
2. Extraia o zip e execute **`Gerar_Relatorio.exe`**.
3. Na primeira execução são criadas, ao lado do `.exe`, as pastas `template/`, `dados_rdo/` e `saida_relatorios/`.
4. (Opcional) Configure as chaves Gemini em *IA → Configurações Gemini...* ou em `template/.env`.

Não é necessário instalar Python.

## Checklist para publicar a Release

1. Confirme que `aplicacao.versao` e `historico_versoes` em `template/sobre.json` estão correctos.
2. Faça push do código desta versão para `main`.
3. Em GitHub → **Releases** → **Create a new release** (ou edite a existente).
4. Use a tag **`{tag}`** e o título **Gerar Relatório {tag}**.
5. Cole o corpo desta secção «Notas desta versão» (e a instalação, se quiser) na descrição.
6. Anexe **apenas** `{nome_zip}` (opcional: também `{nome_sha}`).
7. Marque como **Latest release** e publique.
8. Confirme o download em: {URL_RELEASES}

## Ficheiros gerados por `compilar.bat`

| Ficheiro | Uso |
|----------|-----|
| `Gerar_Relatorio.exe` | Executável (teste local; não anexe solto na Release) |
| `{nome_zip}` | **Anexo principal** da GitHub Release |
| `{nome_sha}` | Hashes SHA-256 (verificação opcional) |
| `{destino.name}` | Este rascunho (não anexar) |

> Não faça commit da pasta `dist/` — está no `.gitignore`.
"""
    destino.write_text(corpo, encoding="utf-8")


def main() -> int:
    try:
        versao, data, notas = _ler_versao()
    except (OSError, ValueError, json.JSONDecodeError) as erro:
        print(f"ERRO: nao foi possivel ler a versao: {erro}", file=sys.stderr)
        return 1

    exe = DIST / EXE_NOME
    if not exe.is_file():
        print(f"ERRO: executavel nao encontrado: {exe}", file=sys.stderr)
        return 1

    DIST.mkdir(parents=True, exist_ok=True)
    nome_zip = f"Gerar_Relatorio_{versao}.zip"
    nome_sha = f"Gerar_Relatorio_{versao}.sha256.txt"
    nome_notas = f"RELEASE_v{versao}.md"
    caminho_zip = DIST / nome_zip
    caminho_sha = DIST / nome_sha
    caminho_notas = DIST / nome_notas

    # Remove zips/sha/notas de versões anteriores (e o zip legado sem versão).
    legado = DIST / "Gerar_Relatorio.zip"
    if legado.is_file():
        legado.unlink(missing_ok=True)
    for antigo in DIST.glob("Gerar_Relatorio_*.zip"):
        if antigo.name != nome_zip:
            antigo.unlink(missing_ok=True)
    for antigo in DIST.glob("Gerar_Relatorio_*.sha256.txt"):
        if antigo.name != nome_sha:
            antigo.unlink(missing_ok=True)
    for antigo in DIST.glob("RELEASE_v*.md"):
        if antigo.name != nome_notas:
            antigo.unlink(missing_ok=True)

    try:
        _criar_zip(exe, caminho_zip)
        digest_exe = _sha256_ficheiro(exe)
        digest_zip = _sha256_ficheiro(caminho_zip)
        _escrever_sha256(
            caminho_sha,
            [(exe, digest_exe), (caminho_zip, digest_zip)],
        )
        _escrever_notas_release(
            caminho_notas,
            versao=versao,
            data=data,
            notas=notas,
            nome_zip=nome_zip,
            nome_sha=nome_sha,
        )
    except OSError as erro:
        print(f"ERRO ao gerar artefactos da Release: {erro}", file=sys.stderr)
        return 1

    tamanho_exe_mb = exe.stat().st_size / (1024 * 1024)
    tamanho_zip_mb = caminho_zip.stat().st_size / (1024 * 1024)
    print(f"VERSAO={versao}")
    print(f"TAG=v{versao}")
    print(f"EXE={exe}")
    print(f"ZIP={caminho_zip}")
    print(f"SHA256={caminho_sha}")
    print(f"NOTAS={caminho_notas}")
    print(f"TAMANHO_EXE_MB={tamanho_exe_mb:.1f}")
    print(f"TAMANHO_ZIP_MB={tamanho_zip_mb:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
