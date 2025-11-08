#!/bin/bash

# DeltaNeutroX Phase 1 - Devnet Deployment Script
# This script deploys the Anchor program to Solana devnet

set -e

echo "🚀 DeltaNeutroX Devnet Deployment"
echo "=================================="
echo ""

# Check if Anchor is installed
if ! command -v anchor &> /dev/null; then
    echo "❌ Anchor is not installed. Please install Anchor first:"
    echo "   cargo install --git https://github.com/coral-xyz/anchor avm --locked --force"
    exit 1
fi

# Check if Solana CLI is installed
if ! command -v solana &> /dev/null; then
    echo "❌ Solana CLI is not installed. Please install it first:"
    echo "   sh -c \"\$(curl -sSfL https://release.solana.com/stable/install)\""
    exit 1
fi

echo "✅ Dependencies check passed"
echo ""

# Set Solana to devnet
echo "📡 Configuring Solana CLI for devnet..."
solana config set --url devnet

# Show current config
echo ""
echo "Current Solana Config:"
solana config get
echo ""

# Check wallet balance
WALLET=$(solana address)
echo "Wallet address: $WALLET"

BALANCE=$(solana balance | awk '{print $1}')
echo "Current balance: $BALANCE SOL"
echo ""

# Airdrop if balance is low
if (( $(echo "$BALANCE < 2" | bc -l) )); then
    echo "💰 Requesting airdrop (2 SOL)..."
    solana airdrop 2
    echo ""

    # Wait a bit for airdrop to confirm
    sleep 2

    NEW_BALANCE=$(solana balance | awk '{print $1}')
    echo "New balance: $NEW_BALANCE SOL"
    echo ""
fi

# Build the program
echo "🔨 Building Anchor program..."
anchor build

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo "✅ Build successful"
echo ""

# Get program ID from target/deploy
PROGRAM_ID=$(solana address -k target/deploy/deltaneutrox_vault-keypair.json)
echo "Program ID: $PROGRAM_ID"
echo ""

# Check if program ID in Anchor.toml matches
echo "Checking Program ID in Anchor.toml..."
TOML_PROGRAM_ID=$(grep "deltaneutrox_vault" Anchor.toml | grep -o '".*"' | tr -d '"')

if [ "$PROGRAM_ID" != "$TOML_PROGRAM_ID" ]; then
    echo "⚠️  WARNING: Program ID mismatch!"
    echo "   Keypair:     $PROGRAM_ID"
    echo "   Anchor.toml: $TOML_PROGRAM_ID"
    echo ""
    echo "Update Anchor.toml with: anchor keys list"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Deploy the program
echo "📤 Deploying to devnet..."
echo "This may take a few minutes..."
echo ""

anchor deploy --provider.cluster devnet

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed"
    exit 1
fi

echo ""
echo "✅ Deployment successful!"
echo ""
echo "═══════════════════════════════════════════"
echo "📋 Deployment Summary"
echo "═══════════════════════════════════════════"
echo ""
echo "Program ID:  $PROGRAM_ID"
echo "Network:     Devnet"
echo "Wallet:      $WALLET"
echo ""
echo "🔗 Explorer:"
echo "https://explorer.solana.com/address/$PROGRAM_ID?cluster=devnet"
echo ""
echo "═══════════════════════════════════════════"
echo ""

# Verify deployment
echo "🔍 Verifying deployment..."
PROGRAM_ACCOUNT=$(solana account $PROGRAM_ID --output json 2>/dev/null || echo "{}")

if echo "$PROGRAM_ACCOUNT" | grep -q "executable"; then
    echo "✅ Program is executable on devnet"
else
    echo "⚠️  Warning: Could not verify program deployment"
fi

echo ""
echo "Next Steps:"
echo "1. Update keeper/.env with PROGRAM_ID=$PROGRAM_ID"
echo "2. Create a vault using CLI: cd cli && npm run create-vault"
echo "3. Run keeper bot: cd keeper && npm run dev"
echo ""
echo "🎉 Deployment complete!"
