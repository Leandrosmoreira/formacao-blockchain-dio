# DeltaNeutroX Phase 1 - Deployment Guide

Complete guide for deploying DeltaNeutroX to Solana devnet and mainnet.

## Prerequisites

### Required Tools

1. **Rust** (1.75+)
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

2. **Solana CLI** (1.18+)
```bash
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"
```

3. **Anchor** (0.30.1)
```bash
cargo install --git https://github.com/coral-xyz/anchor avm --locked --force
avm install 0.30.1
avm use 0.30.1
```

4. **Node.js** (18+)
```bash
# Install via nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```

### Verify Installation

```bash
anchor --version  # Should show: anchor-cli 0.30.1
solana --version  # Should show: solana-cli 1.18.x
node --version    # Should show: v18.x.x
```

## Devnet Deployment

### Step 1: Prepare Wallet

```bash
# Create new wallet (or use existing)
solana-keygen new -o ~/.config/solana/devnet.json

# Set as default
solana config set --keypair ~/.config/solana/devnet.json

# Configure for devnet
solana config set --url devnet

# Verify configuration
solana config get
```

### Step 2: Fund Wallet

```bash
# Airdrop SOL for deployment
solana airdrop 2

# Check balance
solana balance
```

### Step 3: Build Program

```bash
# Build Anchor program
anchor build

# Verify build
ls -la target/deploy/deltaneutrox_vault.so
```

### Step 4: Update Program ID

```bash
# Get program ID from build
anchor keys list

# Update Anchor.toml with the new program ID
# Update programs/deltaneutrox-vault/src/lib.rs declare_id!()

# Rebuild after updating IDs
anchor build
```

### Step 5: Deploy

**Option A: Using Script (Recommended)**
```bash
./scripts/deploy-devnet.sh
```

**Option B: Manual Deployment**
```bash
# Deploy to devnet
anchor deploy --provider.cluster devnet

# Verify deployment
solana program show <PROGRAM_ID> --url devnet
```

### Step 6: Verify Deployment

```bash
# Check program account
solana account <PROGRAM_ID> --url devnet

# View on Explorer
# https://explorer.solana.com/address/<PROGRAM_ID>?cluster=devnet
```

## Post-Deployment Setup

### 1. Update Keeper Bot Configuration

```bash
cd keeper
cp .env.example .env

# Edit .env
nano .env
```

Set:
```bash
SOLANA_RPC_URL=https://api.devnet.solana.com
PROGRAM_ID=<YOUR_DEPLOYED_PROGRAM_ID>
KEEPER_KEYPAIR_PATH=~/.config/solana/devnet.json
```

### 2. Update CLI Configuration

```bash
cd cli
cp .env.example .env

# Edit .env
nano .env
```

Set:
```bash
SOLANA_RPC_URL=https://api.devnet.solana.com
PROGRAM_ID=<YOUR_DEPLOYED_PROGRAM_ID>
WALLET_PATH=~/.config/solana/devnet.json
```

### 3. Create Your First Vault

```bash
cd cli
npm install

# Create vault
npm run create-vault -- \
  --pool HJPjoWUrhoZzkNfRpHuieeFk9WcZWjwy6PBjZ81ngndJ \
  --token-a So11111111111111111111111111111111111111112 \
  --usdc EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --tick-lower -20000 \
  --tick-upper 20000

# Save the VAULT_PUBKEY from output
```

### 4. Test the Vault

```bash
# Deposit
npm run deposit -- \
  --vault <VAULT_PUBKEY> \
  --amount-a 0.1 \
  --amount-usdc 10

# View vault
npm run view-vault -- --vault <VAULT_PUBKEY>

# Withdraw
npm run withdraw -- \
  --vault <VAULT_PUBKEY> \
  --shares 1000
```

### 5. Run Keeper Bot

```bash
cd keeper
npm install

# Edit .env with VAULT_PUBKEY
nano .env

# Start keeper
npm run dev
```

## Mainnet Deployment

⚠️ **WARNING**: Mainnet deployment requires careful preparation and testing.

### Pre-Deployment Checklist

- [ ] All tests passing on devnet
- [ ] Security audit completed
- [ ] Keeper bot tested extensively
- [ ] Emergency procedures documented
- [ ] Sufficient SOL for deployment (~5 SOL minimum)
- [ ] Backup of all keypairs
- [ ] Multisig setup for program authority (recommended)

### Mainnet Steps

```bash
# 1. Configure for mainnet
solana config set --url mainnet-beta

# 2. Use premium RPC (required)
solana config set --url https://mainnet.helius-rpc.com/?api-key=YOUR_KEY

# 3. Check balance (need ~5 SOL)
solana balance

# 4. Build for mainnet
anchor build

# 5. Update program ID
anchor keys list
# Update Anchor.toml and lib.rs

# 6. Rebuild
anchor build

# 7. Deploy (FINAL STEP - irreversible)
anchor deploy --provider.cluster mainnet

# 8. Verify
solana program show <PROGRAM_ID>
```

### Mainnet Configuration

Use premium RPC providers:

**Helius** (Recommended)
```bash
SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY
```

**QuickNode**
```bash
SOLANA_RPC_URL=https://your-endpoint.solana-mainnet.quiknode.pro/YOUR_KEY/
```

**Triton**
```bash
SOLANA_RPC_URL=https://your-endpoint.rpcpool.com/YOUR_KEY
```

## Upgrading Programs

### Anchor Programs Are Immutable

Once deployed, Anchor programs **cannot be upgraded** unless you:

1. Deploy as upgradeable (set in Anchor.toml)
2. Retain upgrade authority
3. Use `anchor upgrade` command

### To Make Program Upgradeable

In `Anchor.toml`:
```toml
[programs.devnet]
deltaneutrox_vault = "PROGRAM_ID"

[programs.mainnet]
deltaneutrox_vault = "PROGRAM_ID"

[provider]
cluster = "devnet"
wallet = "~/.config/solana/id.json"

[scripts]
test = "anchor test"

# Allow upgrades (DO NOT use on mainnet without proper authority management)
[workspace]
members = ["programs/*"]
```

### Upgrade Command

```bash
# Build new version
anchor build

# Upgrade (only if program is upgradeable)
anchor upgrade <PROGRAM_ID> target/deploy/deltaneutrox_vault.so --provider.cluster devnet

# Transfer upgrade authority (for production)
solana program set-upgrade-authority <PROGRAM_ID> --new-upgrade-authority <MULTISIG_OR_NONE>
```

## Monitoring

### Check Program Status

```bash
# View program
solana program show <PROGRAM_ID>

# Get program logs
solana logs <PROGRAM_ID>

# View transaction
solana confirm <TX_SIGNATURE> -v
```

### Keeper Bot Monitoring

```bash
# Check keeper is running
ps aux | grep keeper

# View keeper logs
tail -f keeper/logs/keeper.log

# Monitor vault state
cd cli
npm run view-vault -- --vault <VAULT_PUBKEY>
```

## Troubleshooting

### Build Issues

**Error: `anchor` command not found**
```bash
cargo install --git https://github.com/coral-xyz/anchor avm --locked --force
```

**Error: Wrong Anchor version**
```bash
avm use 0.30.1
```

**Error: Rust version too old**
```bash
rustup update
```

### Deployment Issues

**Error: Insufficient balance**
```bash
# Devnet
solana airdrop 2

# Mainnet
# Transfer SOL from another wallet or exchange
```

**Error: Program ID mismatch**
```bash
# Rebuild after updating lib.rs
anchor build
```

**Error: Deployment timeout**
```bash
# Use premium RPC
solana config set --url https://mainnet.helius-rpc.com/?api-key=YOUR_KEY

# Increase compute budget
solana program deploy --with-compute-unit-price 1000 target/deploy/deltaneutrox_vault.so
```

### Runtime Issues

**Error: Account does not exist**
- Vault not created yet
- Wrong network (devnet vs mainnet)
- Wrong program ID in config

**Error: Unauthorized keeper**
- Keeper keypair doesn't match vault.keeper_authority
- Update vault with correct keeper: use `set_params` (requires vault authority)

**Error: Cooldown not met**
- Wait for cooldown period to elapse
- Check cooldown setting: `view-vault --detailed`

## Security Checklist

Before mainnet deployment:

- [ ] All tests passing
- [ ] Security audit by reputable firm
- [ ] Timelock on upgrades
- [ ] Multisig for critical operations
- [ ] Emergency pause mechanism tested
- [ ] Keeper bot failsafes working
- [ ] Monitoring and alerting setup
- [ ] Incident response plan documented
- [ ] Insurance/bug bounty program considered

## Cost Estimates

### Devnet
- Deploy program: 0 SOL (free airdrops)
- Create vault: ~0.01 SOL
- Transactions: Free

### Mainnet
- Deploy program: ~2-5 SOL (depends on program size)
- Create vault: ~0.01 SOL
- Open position: ~0.005 SOL
- Each transaction: ~0.00005 SOL

## Support

For deployment issues:
- Check logs: `solana logs`
- Discord: Anchor/Solana Discord servers
- GitHub Issues: Create issue with logs

---

**Last Updated**: 2024-11-08
**Version**: 0.3.0
