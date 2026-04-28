# 🔧 INSTRUÇÕES DE COMPILAÇÃO PARA .EXE

## 📋 Pré-requisitos

- **Python 3.7+** instalado globalmente no Windows
- Verificar se Python está no PATH do Windows

---

## ✅ PASSO 1: Verificar se Python está Instalado

Abra o CMD e execute:
```cmd
python --version
```

Se aparecer a versão (ex: Python 3.14.0), está OK! ✅

Se não funcionar, instale Python de: https://www.python.org/downloads/
**IMPORTANTE:** Marque a opção "Add Python to PATH" durante instalação!

---

## ✅ PASSO 2: Compilar para .EXE (RECOMENDADO)

### **Opção A: Duplo-clique (MAIS FÁCIL!) ⭐**
```
COMPILAR_GLOBAL.vbs
```

### **Opção B: Batch File**
```cmd
compilar_exe_global.bat
```

### **Opção C: Manual via CMD**

```cmd
cd D:\Repositorio\Gerar_Relatorio
pip install pyinstaller
python -m pyinstaller --onedir ^
    --windowed ^
    --add-data "saida_relatorios;saida_relatorios" ^
    --add-data "template;template" ^
    --add-data "dados_rdo;dados_rdo" ^
    --collect-all tkcalendar ^
    --collect-all holidays ^
    --collect-all openpyxl ^
    --name "Gerar_Relatorio" ^
    main.py
```

---

## 📁 Estrutura do Compilado

Após a compilação, você terá:

```
dist/
└── Gerar_Relatorio/
    ├── Gerar_Relatorio.exe        ← EXECUTE ESTE ARQUIVO
    ├── saida_relatorios/          ← Pasta de relatórios (acesso fácil)
    ├── template/                  ← Templates do Excel
    ├── dados_rdo/                 ← Dados dos RDOs
    └── [outras dependências]
```

**Para usar o programa compilado:**
1. Abra a pasta `dist\Gerar_Relatorio\`
2. Duplo-clique em `Gerar_Relatorio.exe`
3. Os relatórios gerados estarão em `saida_relatorios/`

---

## ⚙️ Verificações

### Verificar Python instalado:
```cmd
python --version
```

### Verificar PyInstaller instalado:
```cmd
pip show pyinstaller
```

### Limpar compilações anteriores:
```cmd
rmdir /s /q build
rmdir /s /q dist
```

---

## ❓ Problemas Comuns

### "Python não é reconhecido"
- Python não está no PATH do Windows
- Solução: Reinstale Python e marque "Add Python to PATH"

### "PyInstaller não é reconhecido"
- Instale manualmente: `pip install pyinstaller`

### "Arquivo não encontrado: saida_relatorios"
- Certifique-se de que está na pasta raiz do projeto
- Verifique os caminhos das pastas

### Compilação muito lenta
- Isso é NORMAL! PyInstaller leva 2-5 minutos
- Aguarde a conclusão (não feche a janela)

### "ConnectionResetError" durante instalação
- Problema de conexão com internet
- Tente novamente ou use: `pip install --no-cache-dir pyinstaller`

---

## 📝 Notas

- O executável é **auto-contido** e pode ser executado em qualquer PC com Windows
- Python **não precisa estar instalado** no PC do usuário final
- A pasta `saida_relatorios` fica na raiz da distribuição para fácil acesso
- Tamanho do executável: ~150-200MB (contém todas as bibliotecas necessárias)

