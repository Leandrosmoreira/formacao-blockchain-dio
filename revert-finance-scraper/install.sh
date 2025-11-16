#!/bin/bash
# Script de instalação do Web Scraper do Revert Finance

echo "================================================"
echo "Instalação do Revert Finance Web Scraper"
echo "================================================"
echo ""

# Verifica Python
echo "🐍 Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3.8 ou superior."
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION encontrado"
echo ""

# Cria ambiente virtual
echo "📦 Criando ambiente virtual..."
python3 -m venv venv
echo "✅ Ambiente virtual criado"
echo ""

# Ativa ambiente virtual
echo "🔌 Ativando ambiente virtual..."
source venv/bin/activate
echo ""

# Instala dependências
echo "📥 Instalando dependências Python..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependências Python instaladas"
echo ""

# Opção: Instalar Playwright
echo "🎭 Deseja instalar Playwright? (Recomendado para melhor desempenho)"
echo "   Digite 'y' para sim, 'n' para usar apenas Selenium:"
read -p "> " INSTALL_PLAYWRIGHT

if [ "$INSTALL_PLAYWRIGHT" = "y" ] || [ "$INSTALL_PLAYWRIGHT" = "Y" ]; then
    echo "📥 Instalando Playwright..."
    pip install playwright
    echo "🌐 Instalando navegadores do Playwright..."
    playwright install chromium
    echo "✅ Playwright instalado"
else
    echo "⏭️  Pulando instalação do Playwright"
    echo "ℹ️  Usando Selenium. Certifique-se de ter Chrome/Chromium instalado:"
    echo "   Ubuntu/Debian: sudo apt-get install chromium-browser"
    echo "   macOS: brew install chromium"
fi
echo ""

echo "================================================"
echo "✅ Instalação concluída!"
echo "================================================"
echo ""
echo "Para usar o scraper:"
echo ""
echo "1. Ative o ambiente virtual:"
echo "   source venv/bin/activate"
echo ""
echo "2. Execute o scraper:"
echo "   python scraper.py           # Selenium"
echo "   python scraper_playwright.py # Playwright (se instalado)"
echo ""
echo "3. Os dados serão salvos em arquivos CSV"
echo ""
