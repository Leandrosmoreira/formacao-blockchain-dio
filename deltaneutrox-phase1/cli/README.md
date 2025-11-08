# CLI Scripts

Command-line interface scripts for interacting with DeltaNeutroX vaults.

## Status

✅ **Implemented** - Ready to use

## Available Scripts

### Core Operations

**create-vault.ts**
```bash
# Create a new vault for a Whirlpool pool
yarn cli:create-vault \
  --pool <WHIRLPOOL_ID> \
  --tick-lower -20000 \
  --tick-upper 20000 \
  --slippage 100 \
  --force-swap true
```

**deposit.ts**
```bash
# Deposit tokens and receive vault shares
yarn cli:deposit \
  --vault <VAULT_ID> \
  --amount-a 1.0 \
  --amount-usdc 100
```

**withdraw.ts**
```bash
# Burn shares and withdraw tokens
yarn cli:withdraw \
  --vault <VAULT_ID> \
  --shares 1000
```

**view-vault.ts**
```bash
# View vault state and balances
yarn cli:view-vault --vault <VAULT_ID>
```

### Position Management

**open-position.ts**
```bash
# Open LP position (keeper operation)
yarn cli:open-position \
  --vault <VAULT_ID> \
  --liquidity 1000000
```

**exit-position.ts**
```bash
# Exit position (keeper operation)
yarn cli:exit-position --vault <VAULT_ID>
```

**reenter-position.ts**
```bash
# Re-enter position (keeper operation)
yarn cli:reenter-position \
  --vault <VAULT_ID> \
  --liquidity 1000000
```

### Configuration

**set-params.ts**
```bash
# Update vault parameters
yarn cli:set-params \
  --vault <VAULT_ID> \
  --deadband 75 \
  --cooldown 300000
```

## Installation

```bash
cd cli
npm install

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

## Dependencies

```json
{
  "@coral-xyz/anchor": "^0.30.1",
  "@solana/web3.js": "^1.95.0",
  "@solana/spl-token": "^0.4.0",
  "commander": "^11.0.0",
  "inquirer": "^9.0.0",
  "chalk": "^5.3.0",
  "ora": "^7.0.0"
}
```

## Usage Examples

```bash
# Install
cd cli
npm install

# Configure
export SOLANA_RPC_URL=https://api.devnet.solana.com
export WALLET_PATH=~/.config/solana/id.json

# Create vault
npm run create-vault -- \
  --pool HJPjoWUrhoZzkNfRpHuieeFk9WcZWjwy6PBjZ81ngndJ \
  --tick-lower -20000 \
  --tick-upper 20000

# Deposit
npm run deposit -- \
  --vault <VAULT_ID> \
  --amount-sol 10 \
  --amount-usdc 1000

# View
npm run view-vault -- --vault <VAULT_ID>
```

## Environment Configuration

Create a `.env` file:

```bash
SOLANA_RPC_URL=https://api.devnet.solana.com
WALLET_PATH=~/.config/solana/id.json
PROGRAM_ID=Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS
```

## Troubleshooting

**"Wallet file not found"**
- Check WALLET_PATH in .env
- Generate wallet: `solana-keygen new`

**"Insufficient balance"**
- Airdrop SOL: `solana airdrop 2`

**"Account does not exist"**
- Wrong vault address
- Vault not created yet

## Implementation Details

All scripts use:
- Anchor IDL integration for type-safe transactions
- PDA derivation for vault authority
- Token account management (ATA)
- Comprehensive error handling
- Colored console output (chalk)
- Loading spinners (ora)

See [src/utils.ts](src/utils.ts) for shared utilities.
