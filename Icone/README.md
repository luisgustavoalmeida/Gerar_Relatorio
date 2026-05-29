# 🎨 Conversão de Ícones - Gerar_Relatorio

Esta pasta contém os ícones da aplicação e ferramentas para gerá-los.

## 📁 Arquivos

- **icone.png** - Ícone original em formato PNG (recomendado para edição)
- **icone.ico** - Ícone compilado em formato ICO (usado pela aplicação)
- **converter_png_para_ico.py** - Script para converter PNG → ICO (com qualidade máxima)
- **README.md** - Este arquivo
- **GUIA_QUALIDADE.md** - Guia completo sobre manutenção de qualidade ⭐

## 🚀 Como usar

### 1️⃣ Instalar dependência (primeira vez)

```powershell
pip install pillow
```

### 2️⃣ Converter PNG para ICO

Se você editou o `icone.png` e precisa gerar um novo `icone.ico`:

```powershell
cd Icone
python converter_png_para_ico.py
```

Ou a partir da raiz do projeto:

```powershell
python Icone\converter_png_para_ico.py
```

O script automaticamente:
- ✅ Valida qualidade da imagem (resolução, modo de cores)
- ✅ Converte para RGBA (com transparência)
- ✅ Redimensiona com LANCZOS (máxima qualidade)
- ✅ Cria múltiplos tamanhos (256, 128, 64, 48, 32, 16px)
- ✅ Salva como `icone.ico`
- ✅ Faz backup da versão anterior

### 3️⃣ Compilar com o novo ícone

Após gerar o `.ico`, recompile a aplicação:

```powershell
.\compilar_exe_global.bat
```

## 📋 O que o script faz

1. ✅ Valida que `icone.png` existe e tem qualidade adequada
2. ✅ Verifica resolução mínima (avisos se < 256×256)
3. ✅ Converte para modo RGBA (preserva transparência)
4. ✅ Cria múltiplos tamanhos (256, 128, 64, 48, 32, 16 pixels)
5. ✅ Usa interpolação LANCZOS (melhor qualidade disponível)
6. ✅ Salva como `icone.ico` com todos os tamanhos inclusos
7. ✅ Faz backup automático (`icone.ico.bak`)
8. ✅ Pronto para usar com PyInstaller

## 🎯 Formato recomendado

- **Tipo:** PNG com fundo transparente (.png)
- **Resolução:** 512×512 pixels ou maior (mínimo 256×256)
- **Proporção:** Quadrado (1:1)
- **Modo de cores:** RGBA (com canal alpha para transparência)
- **Fundo:** Transparente (não branco ou colorido)
- **Anti-aliasing:** Ativado (bordas suaves)

## 🎨 Como manter MÁXIMA qualidade

> ⭐ **Consulte o arquivo `GUIA_QUALIDADE.md` para um guia completo!**

Resumo rápido:

```
✅ FAÇA:
  • Use PNG com transparência (RGBA)
  • Resolução original ≥ 512×512 pixels
  • Quadrado (1:1)
  • Fundo transparente
  • Detalhes > 2 pixels
  • Gradientes suaves

❌ NÃO FAÇA:
  • Use JPG/JPEG (não suporta transparência)
  • Imagens com resolução < 256×256
  • Fundo branco ou colorido
  • Muitos detalhes muito pequenos (< 2px)
  • Paletas limitadas (use RGB/RGBA completo)
```

## 🛠️ Ferramentas Recomendadas

- **GIMP** (Grátis) - https://www.gimp.org/
- **Inkscape** (Grátis) - https://inkscape.org/
- **Paint.NET** (Grátis) - https://www.getpaint.net/
- **Photoshop** (Pago) - Adobe

## ❓ Troubleshooting

**Erro: "Pillow não está instalado"**
```powershell
pip install --upgrade pillow
```

**Erro: "Arquivo icone.png não encontrado"**
- Certifique-se que `icone.png` está nesta pasta
- Coloque o arquivo aqui e tente novamente

**Erro: "Resolução abaixo do recomendado"**
- Use imagem com 512×512 ou maior
- O script permite prosseguir mesmo assim, mas qualidade pode ser afetada

**O ícone não aparece na aplicação após compilar**
- Limpe as pastas `build/` e `dist/`
- Recompile com `compilar_exe_global.bat`
- Reinicie o Windows Explorer (Ctrl+Shift+Esc → Explorer → Reiniciar)
- Aguarde (o Windows pode cachejar ícones antigos)

**Ícone aparece pixelado/com dentes de serra**
- Use imagem original maior (512×512+)
- Simplifique detalhes muito pequenos
- Reconverta e recompile

## 📝 Exemplo completo

```powershell
# 1. Editar icone.png em seu editor favorito (GIMP, Inkscape, etc)
#    - Resolução: 512×512
#    - Fundo: Transparente
#    - Salve em: Icone/icone.png

# 2. Converter para ICO
cd C:\Repositorio\Gerar_Relatorio\Icone
python converter_png_para_ico.py
# Saída: ✅ SUCESSO! Arquivo gerado: icone.ico

# 3. Compilar aplicação
cd ..
.\compilar_exe_global.bat
# Aguarde 2-5 min...

# 4. Testar executável
.\dist\Gerar_Relatorio\Gerar_Relatorio.exe

# 5. Verificar ícone no Explorer
# Clique direito no .exe → Propriedades
# O ícone deve aparecer com seu design!
```

## 📚 Leitura Complementar

Veja o arquivo **`GUIA_QUALIDADE.md`** para:
- Resoluções recomendadas por caso de uso
- Algoritmos de interpolação explicados
- Comparação de ferramentas gráficas
- Checklist completo de qualidade
- Pipeline recomendado passo a passo
- Dicas avançadas

---
**Última atualização:** 2026-05-20  
**Script versão:** 2.0 (Otimizado para qualidade máxima)

