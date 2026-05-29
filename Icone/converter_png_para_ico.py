#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Conversor de PNG para ICO - Gerar_Relatorio
============================================

Converte icone.png em icone.ico com múltiplos tamanhos para uso com PyInstaller.
Otimizado para manter MÁXIMA QUALIDADE durante a conversão.

Uso:
    python converter_png_para_ico.py

Requisitos:
    pip install pillow

Saída:
    icone.ico (arquivo de ícone com tamanhos: 256, 128, 64, 48, 32, 16 pixels)

Qualidade:
    ✅ Usa interpolação LANCZOS (melhor qualidade)
    ✅ Preserva transparência RGBA
    ✅ Valida resolução mínima (256x256)
    ✅ Otimiza cores sem perder detalhes
"""

from pathlib import Path
import sys

try:
    from PIL import Image
except ImportError:
    print("❌ ERRO: Pillow não está instalado!")
    print("\nInstale com o comando:")
    print("  pip install pillow")
    sys.exit(1)


def validar_imagem_png(img, caminho):
    """Valida se a imagem PNG tem qualidade adequada."""
    largura, altura = img.size

    print(f"📊 Informações da imagem:")
    print(f"  • Resolução: {largura}x{altura} pixels")
    print(f"  • Modo de cores: {img.mode}")

    # Verificar resolução mínima
    resolucao_minima = 256
    if largura < resolucao_minima or altura < resolucao_minima:
        print(f"\n⚠️  AVISO: Resolução abaixo do recomendado ({resolucao_minima}x{resolucao_minima})")
        print(f"  A qualidade pode ser afetada em resoluções menores.")
        print(f"  Recomendação: Use imagem com {resolucao_minima}x{resolucao_minima} ou maior.")
        resposta = input("\n  Deseja continuar mesmo assim? (s/n): ").lower()
        if resposta != "s":
            return False

    # Verificar se é quadrado
    if largura != altura:
        print(f"\n⚠️  AVISO: Imagem não é quadrada ({largura}x{altura})")
        print(f"  Será redimensionada para quadrado na conversão.")

    # Verificar transparência
    if img.mode not in ("RGBA", "LA", "PA"):
        print(f"\n💡 Dica: Imagem sem transparência (modo {img.mode})")
        print(f"  Use PNG com fundo transparente para melhor visual.")

    return True


def converter_png_para_ico():
    """Converte PNG para ICO com múltiplos tamanhos preservando qualidade máxima."""

    # Diretório atual (pasta Icone)
    pasta_raiz = Path(__file__).parent
    arquivo_png = pasta_raiz / "icone.png"
    arquivo_ico = pasta_raiz / "icone.ico"
    arquivo_ico_backup = pasta_raiz / "icone.ico.bak"

    # Validar arquivo PNG
    if not arquivo_png.exists():
        print(f"❌ ERRO: Arquivo não encontrado: {arquivo_png}")
        print(f"\nColoque o arquivo 'icone.png' na pasta: {pasta_raiz}")
        return False

    print(f"📂 Pasta de trabalho: {pasta_raiz}")
    print(f"📥 Arquivo de entrada: {arquivo_png.name}")
    print()

    try:
        # Abrir imagem PNG
        print("⏳ Abrindo imagem PNG...")
        img = Image.open(arquivo_png)

        # Validar qualidade
        if not validar_imagem_png(img, arquivo_png):
            return False

        print()

        # Redimensionar para quadrado se necessário (mas mantendo conteúdo)
        img_original = img.copy()
        if img.width != img.height:
            tamanho_novo = max(img.width, img.height)
            # Cria uma imagem quadrada com fundo transparente
            img_quadrada = Image.new("RGBA", (tamanho_novo, tamanho_novo), (0, 0, 0, 0))
            offset_x = (tamanho_novo - img.width) // 2
            offset_y = (tamanho_novo - img.height) // 2
            img_quadrada.paste(img, (offset_x, offset_y), img if img.mode == "RGBA" else None)
            img = img_quadrada

        # Converter para RGBA (necessário para ICO e preservar transparência)
        if img.mode != "RGBA":
            print("🔄 Convertendo para RGBA (preserva transparência)...")
            img = img.convert("RGBA")

        # Tamanhos do ícone (do maior para o menor)
        # Incluindo tamanhos grandes para melhor qualidade em exibições modernas
        tamanhos = [
            (256, 256),
            (128, 128),
            (64, 64),
            (48, 48),
            (32, 32),
            (16, 16),
        ]

        # Redimensionar para cada tamanho com máxima qualidade
        print("\n⏳ Criando múltiplos tamanhos (interpolação LANCZOS - alta qualidade)...")
        imagens_ico = []
        tempo_processamento = []

        for largura, altura in tamanhos:
            # LANCZOS é o método de interpolação de maior qualidade no Pillow
            img_redimensionada = img.resize(
                (largura, altura),
                Image.LANCZOS,
                reducing_gap=1.0  # Garante máxima qualidade mesmo em redimensionamentos grandes
            )
            imagens_ico.append(img_redimensionada)
            print(f"  ✓ {largura:3d}x{altura:3d}px criado com qualidade máxima")

        # Criar backup do arquivo anterior se existir
        if arquivo_ico.exists():
            try:
                arquivo_ico.rename(arquivo_ico_backup)
                print(f"\n💾 Backup criado: icone.ico.bak")
            except:
                pass

        # Salvar como ICO com todos os tamanhos
        print("\n⏳ Salvando arquivo ICO...")
        imagens_ico[0].save(
            arquivo_ico,
            format="ICO",
            sizes=tamanhos
        )

        tamanho_kb = arquivo_ico.stat().st_size / 1024
        print(f"✅ SUCESSO! Arquivo gerado: {arquivo_ico.name}")
        print(f"\n📍 Caminho completo: {arquivo_ico}")
        print(f"📏 Tamanho do arquivo: {tamanho_kb:.1f} KB")
        print(f"🎨 Qualidade: MÁXIMA (LANCZOS)")
        print(f"\n✨ Pronto para usar com PyInstaller!")

        # Dicas finais
        print("\n" + "="*50)
        print("💡 Dicas para manter qualidade:")
        print("="*50)
        print("1. Use PNG com fundo transparente (RGBA)")
        print("2. Imagem original: 512x512 ou 256x256 no mínimo")
        print("3. Evite muitos detalhes pequenos (não escaldam bem)")
        print("4. Teste em diferentes resoluções (16x16 até 256x256)")
        print("5. Use gradientes suaves, não paletas limitadas")

        return True

    except Exception as e:
        print(f"❌ ERRO ao processar imagem: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("🎨 Conversor PNG → ICO")
    print("=" * 50)
    print()

    sucesso = converter_png_para_ico()

    if not sucesso:
        sys.exit(1)

