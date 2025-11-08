#!/bin/bash

# Script para enviar DeltaNeutroX para um novo repositório

echo "📦 Preparando DeltaNeutroX para novo repositório..."
echo ""

# Verificar se a URL foi passada
if [ -z "$1" ]; then
    echo "❌ Erro: URL do repositório não fornecida"
    echo ""
    echo "Uso:"
    echo "  ./PUSH_TO_NEW_REPO.sh <URL_DO_REPO>"
    echo ""
    echo "Exemplo:"
    echo "  ./PUSH_TO_NEW_REPO.sh https://github.com/SEU_USUARIO/deltaneutrox-phase1.git"
    echo ""
    exit 1
fi

NEW_REPO_URL=$1

echo "🎯 Novo repositório: $NEW_REPO_URL"
echo ""

# Criar diretório temporário
TEMP_DIR=$(mktemp -d)
echo "📁 Criando cópia temporária em: $TEMP_DIR"

# Copiar apenas a pasta deltaneutrox-phase1
cp -r . "$TEMP_DIR/"
cd "$TEMP_DIR"

# Remover git existente (se houver)
rm -rf .git

# Inicializar novo git
echo "🔧 Inicializando novo repositório Git..."
git init
git add .
git commit -m "Initial commit - DeltaNeutroX Phase 1 Complete

DeltaNeutroX - Delta-Neutral Liquidity Strategy on Solana
==========================================================

Complete Phase 1 implementation (100%) including:

Core Components:
- ✅ Anchor program with delta-neutral strategy
- ✅ Keeper bot for automated position management
- ✅ CLI tools for vault management
- ✅ Comprehensive test suite (19 tests)

Features:
- Orca Whirlpool concentrated liquidity integration
- Jupiter V6 swap aggregation
- Pyth price feed monitoring
- TWAP-based re-entry strategy
- Pro-rata share distribution
- Hysteresis control (deadband + cooldown)

Technical Stack:
- Solana/Anchor 0.30.1
- Rust 1.75+
- TypeScript/Node.js
- SPL Token Program
- Cross-program invocations (CPI)

Documentation:
- Complete deployment guides (English + Portuguese)
- Test coverage documentation
- API documentation
- Troubleshooting guides

Project Structure:
- programs/deltaneutrox-vault/    # Anchor program (Rust)
- keeper/                          # Automated keeper bot
- cli/                             # Command-line tools
- tests/                           # Unit + E2E tests
- scripts/                         # Deployment scripts
- docs/                            # Documentation

Status: Ready for devnet deployment
License: MIT
"

# Adicionar remote
echo "🔗 Configurando remote..."
git branch -M main
git remote add origin "$NEW_REPO_URL"

# Push
echo "📤 Enviando para o repositório..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Projeto enviado com sucesso!"
    echo ""
    echo "🔗 Seu repositório: ${NEW_REPO_URL%.git}"
    echo ""
    echo "📋 Próximos passos:"
    echo "1. Acesse o repositório no GitHub"
    echo "2. Clone para sua máquina: git clone $NEW_REPO_URL"
    echo "3. Siga o GUIA_DEPLOY.md para fazer deploy na devnet"
    echo ""
else
    echo ""
    echo "❌ Erro ao enviar para o repositório"
    echo "Verifique se a URL está correta e se você tem permissão"
    echo ""
fi

# Limpar
cd -
rm -rf "$TEMP_DIR"
