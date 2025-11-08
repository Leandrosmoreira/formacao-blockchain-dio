# CLI Scripts

Command-line interface scripts for interacting with DeltaNeutroX vaults.

## Status

⚠️ **Not yet implemented** - Coming soon

## Planned Scripts

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

## Implementation Plan

1. Create `package.json` with dependencies
2. Implement core scripts (create, deposit, withdraw, view)
3. Add keeper operation scripts
4. Add utility functions (PDA derivation, account fetching)
5. Add interactive prompts (inquirer.js)
6. Add validation and error handling

## Dependencies (Planned)

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

## Usage Example (Future)

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

## Contributing

To implement these scripts:

1. Use the keeper's IDL integration as reference
2. Reuse PDA derivation from `keeper/src/pda.ts`
3. Follow Anchor best practices
4. Add comprehensive error handling
5. Include help messages and examples

See [keeper/src/](../keeper/src/) for implementation patterns.
