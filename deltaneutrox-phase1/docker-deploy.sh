#!/bin/bash
set -e

echo "🐳 DeltaNeutroX - Docker Deploy Script"
echo "======================================"
echo ""

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Função para exibir mensagens
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Build da imagem Docker
info "Construindo imagem Docker..."
docker compose build

# 2. Iniciar container
info "Iniciando container..."
docker compose up -d

# 3. Copiar keypair (se existir)
if [ -f "$HOME/.config/solana/id.json" ]; then
    info "Copiando keypair existente..."
    docker compose exec -T deltaneutrox mkdir -p /root/.config/solana
    docker cp "$HOME/.config/solana/id.json" deltaneutrox-builder:/root/.config/solana/id.json
else
    warn "Nenhuma keypair encontrada. Criando nova..."
    docker compose exec deltaneutrox solana-keygen new --outfile /root/.config/solana/id.json --no-bip39-passphrase
fi

# 4. Configurar Solana para devnet
info "Configurando Solana CLI para devnet..."
docker compose exec deltaneutrox solana config set --url https://api.devnet.solana.com

# 5. Verificar saldo
info "Verificando saldo..."
BALANCE=$(docker compose exec -T deltaneutrox solana balance | grep -oP '\d+(\.\d+)?' | head -1)
ADDRESS=$(docker compose exec -T deltaneutrox solana address)

echo ""
echo "📍 Endereço da carteira: $ADDRESS"
echo "💰 Saldo atual: $BALANCE SOL"
echo ""

if (( $(echo "$BALANCE < 2" | bc -l) )); then
    warn "Saldo insuficiente! Solicitando airdrop..."
    docker compose exec deltaneutrox solana airdrop 2 || warn "Airdrop falhou. Use: https://faucet.solana.com"
    sleep 5
fi

# 6. Build do programa
info "Compilando programa Anchor..."
docker compose exec deltaneutrox anchor build

# 7. Verificar se build foi bem-sucedido
if docker compose exec -T deltaneutrox test -f target/deploy/deltaneutrox_vault.so; then
    info "✅ Build concluído com sucesso!"
else
    error "❌ Build falhou!"
    exit 1
fi

# 8. Deploy
info "Fazendo deploy na devnet..."
docker compose exec deltaneutrox anchor deploy --provider.cluster devnet

# 9. Verificar deploy
if [ $? -eq 0 ]; then
    echo ""
    info "🎉 DEPLOY CONCLUÍDO COM SUCESSO!"
    echo ""
    info "📋 Próximos passos:"
    echo "   1. Acessar container: docker compose exec deltaneutrox bash"
    echo "   2. Verificar logs: docker compose logs -f"
    echo "   3. Parar container: docker compose down"
    echo ""
else
    error "❌ Deploy falhou!"
    exit 1
fi
