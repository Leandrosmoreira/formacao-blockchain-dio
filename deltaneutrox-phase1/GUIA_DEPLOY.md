# Guia de Deploy na Devnet - DeltaNeutroX

## Pré-requisitos

### 1. Instalar Anchor CLI (se ainda não tiver)
```bash
cargo install --git https://github.com/coral-xyz/anchor avm --locked --force
avm install latest
avm use latest
```

### 2. Instalar Solana CLI (se ainda não tiver)
```bash
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"
```

### 3. Verificar instalações
```bash
anchor --version  # Deve mostrar v0.30.1 ou superior
solana --version  # Deve mostrar v1.18 ou superior
```

---

## Passo a Passo do Deploy

### Passo 1: Configurar Solana para Devnet
```bash
cd deltaneutrox-phase1
solana config set --url devnet
```

Verifique a configuração:
```bash
solana config get
```

Deve mostrar:
```
RPC URL: https://api.devnet.solana.com
```

### Passo 2: Criar/Verificar Carteira
```bash
# Ver endereço da carteira atual
solana address

# Se não tiver carteira, criar uma nova
solana-keygen new --outfile ~/.config/solana/id.json
```

### Passo 3: Solicitar Airdrop (SOL grátis na devnet)
```bash
# Verificar saldo atual
solana balance

# Solicitar 2 SOL (necessário para deploy)
solana airdrop 2

# Aguardar confirmação e verificar novo saldo
solana balance
```

**Nota:** Se o airdrop falhar (limite de rate), tente:
- Aguardar alguns minutos e tentar novamente
- Usar faucet web: https://faucet.solana.com

### Passo 4: Compilar o Programa
```bash
anchor build
```

Isso irá:
- Compilar o programa Rust
- Gerar o arquivo IDL (Interface Definition Language)
- Criar keypair do programa em `target/deploy/deltaneutrox_vault-keypair.json`

### Passo 5: Verificar Program ID
```bash
# Ver o Program ID que será usado
solana address -k target/deploy/deltaneutrox_vault-keypair.json

# Listar todas as chaves
anchor keys list
```

### Passo 6: Atualizar Anchor.toml (se necessário)
```bash
# O Program ID em Anchor.toml deve corresponder ao keypair
# Se não corresponder, atualize com:
anchor keys sync
```

### Passo 7: Fazer o Deploy
```bash
anchor deploy --provider.cluster devnet
```

Isso irá:
- Fazer upload do programa compilado para devnet
- Custo: ~2-3 SOL (que volta para a carteira se re-deployar)
- Tempo: 1-3 minutos

### Passo 8: Verificar Deployment
```bash
# Salvar o Program ID (mostrado no output do deploy)
export PROGRAM_ID=<SEU_PROGRAM_ID>

# Verificar se o programa está no chain
solana program show $PROGRAM_ID

# Ver no Explorer
echo "https://explorer.solana.com/address/$PROGRAM_ID?cluster=devnet"
```

---

## Pós-Deploy - Configuração

### 1. Atualizar Keeper Bot
```bash
cd keeper

# Criar/atualizar .env
cat > .env << END
SOLANA_RPC_URL=https://api.devnet.solana.com
PROGRAM_ID=$PROGRAM_ID
WALLET_PATH=/caminho/para/sua/wallet.json
CHECK_INTERVAL=60000
END
```

### 2. Atualizar CLI
```bash
cd ../cli

# Criar/atualizar .env
cat > .env << END
SOLANA_RPC_URL=https://api.devnet.solana.com
PROGRAM_ID=$PROGRAM_ID
WALLET_PATH=/caminho/para/sua/wallet.json
END
```

### 3. Instalar Dependências
```bash
# Keeper
cd ../keeper
npm install

# CLI
cd ../cli
npm install
```

---

## Testando o Deployment

### Teste 1: Criar um Vault
```bash
cd cli
npm run create-vault -- \
  --pool-id <WHIRLPOOL_ID> \
  --tick-lower -20000 \
  --tick-upper 20000 \
  --slippage 100
```

### Teste 2: Visualizar Vault
```bash
npm run view-vault -- --vault <VAULT_ADDRESS>
```

### Teste 3: Fazer Deposit
```bash
npm run deposit -- \
  --vault <VAULT_ADDRESS> \
  --amount-a 1 \
  --amount-usdc 100
```

### Teste 4: Iniciar Keeper Bot
```bash
cd ../keeper
npm run dev
```

O keeper deve:
- Conectar ao programa na devnet
- Monitorar vaults a cada 60 segundos
- Logar atividades

---

## Troubleshooting

### Erro: "Insufficient funds"
**Solução:** Solicitar mais SOL:
```bash
solana airdrop 2
```

### Erro: "Program ID mismatch"
**Solução:** Sincronizar chaves:
```bash
anchor keys sync
anchor build
anchor deploy --provider.cluster devnet
```

### Erro: "Airdrop rate limit"
**Solução:** 
- Aguardar 5-10 minutos
- Usar faucet web: https://faucet.solana.com

### Erro: "Build failed"
**Solução:** Verificar versões:
```bash
rustc --version  # Deve ser 1.75+
anchor --version  # Deve ser 0.30.1+
solana --version  # Deve ser 1.18+
```

### Erro: "RPC request failed"
**Solução:** Trocar RPC URL:
```bash
# Opção 1: Alchemy
export SOLANA_RPC_URL=https://solana-devnet.g.alchemy.com/v2/YOUR_KEY

# Opção 2: Quicknode
export SOLANA_RPC_URL=https://YOUR_ENDPOINT.solana-devnet.quiknode.pro/

# Opção 3: Public RPC
export SOLANA_RPC_URL=https://api.devnet.solana.com
```

---

## Comandos Úteis

### Ver logs do programa
```bash
solana logs $PROGRAM_ID
```

### Ver saldo da carteira
```bash
solana balance
```

### Ver informações do programa
```bash
solana program show $PROGRAM_ID
```

### Re-deploy (atualizar programa)
```bash
anchor build
anchor deploy --provider.cluster devnet
```

### Fechar programa (recuperar SOL)
```bash
solana program close $PROGRAM_ID --bypass-warning
```

---

## Custos Estimados (Devnet)

- Deploy inicial: ~2-3 SOL (retornável)
- Criar vault: ~0.005 SOL
- Deposit/Withdraw: ~0.001 SOL
- Transações keeper: ~0.0001 SOL cada

**Total para testes completos: ~0.1 SOL** (tudo grátis via airdrop)

---

## Links Úteis

- Solana Explorer (Devnet): https://explorer.solana.com/?cluster=devnet
- Faucet Devnet: https://faucet.solana.com
- Anchor Docs: https://www.anchor-lang.com
- Solana CLI Docs: https://docs.solana.com/cli

---

## Checklist de Deploy

- [ ] Anchor CLI instalado
- [ ] Solana CLI instalado  
- [ ] Configurado para devnet
- [ ] Carteira com >= 2 SOL
- [ ] Programa compilado (`anchor build`)
- [ ] Program ID sincronizado
- [ ] Deploy executado
- [ ] Programa verificado no Explorer
- [ ] Keeper .env configurado
- [ ] CLI .env configurado
- [ ] Dependências instaladas (npm install)
- [ ] Vault de teste criado
- [ ] Keeper bot funcionando

---

✅ Após completar todos os passos, seu programa estará 100% funcional na devnet!
