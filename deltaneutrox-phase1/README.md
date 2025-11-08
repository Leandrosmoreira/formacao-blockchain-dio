# DeltaNeutroX Phase 1 - Vault with Auto-Exit Strategy

Automated liquidity provision vault on Solana with intelligent auto-exit and re-entry mechanisms for Orca Whirlpool pools.

## Features

- **Automated LP Management**: Manages liquidity positions in Orca Whirlpool pools
- **Auto-Exit**: Automatically exits positions when price moves outside configured range
- **Smart Re-entry**: Re-enters positions based on TWAP with hysteresis (deadband + cooldown)
- **Share-based**: Users receive vault shares representing their pro-rata ownership
- **Secure**: PDA-based authority, reentrancy protection, slippage controls

## Project Structure

```
deltaneutrox-phase1/
├── programs/
│   └── deltaneutrox-vault/      # Anchor program
│       ├── src/
│       │   ├── state/            # Vault and config state
│       │   ├── instructions/     # Program instructions
│       │   ├── cpi/              # Cross-program invocations
│       │   ├── errors.rs         # Custom errors
│       │   ├── events.rs         # Program events
│       │   └── constants.rs      # Constants and configs
│       └── Cargo.toml
├── tests/                        # Anchor tests
├── cli/                          # CLI scripts
├── keeper/                       # Keeper bot (auto-exit/reentry)
├── Anchor.toml
└── package.json
```

## Quick Start

### Prerequisites

- Rust 1.75+
- Solana CLI 1.18+
- Anchor 0.30.1
- Node.js 18+
- Yarn

### Installation

```bash
# Clone repository
cd deltaneutrox-phase1

# Install dependencies
yarn install

# Build program
anchor build

# Run tests
anchor test
```

### Deploy to Devnet

```bash
# Configure Solana CLI for devnet
solana config set --url devnet

# Airdrop SOL for testing
solana airdrop 2

# Deploy program using script
./scripts/deploy-devnet.sh

# Or manually
anchor deploy --provider.cluster devnet
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide.

## Program Instructions

### Core Operations

1. **create_vault** - Initialize a new vault for a Whirlpool pool
2. **deposit** - Deposit tokens and receive vault shares
3. **withdraw** - Burn shares and withdraw pro-rata tokens

### Position Management

4. **open_position_once** - Open LP position in Whirlpool
5. **decrease_liquidity_all** - Exit position (decrease 100%)
6. **collect_fees** - Collect accumulated fees
7. **swap_all_to_usdc** - Swap token_a to USDC
8. **mark_exited_to_usdc** - Mark vault as exited

### Re-entry

9. **reenter_with_liquidity** - Re-enter position after cooldown
10. **set_params** - Update vault configuration

## Configuration Parameters

- **deadband_bps**: Hysteresis band (default: 50 = 0.5%)
- **twap_window_secs**: TWAP calculation window (default: 60s)
- **cooldown_ms**: Minimum wait before re-entry (default: 180000 = 3min)
- **slippage_bps**: Max slippage tolerance (default: 100 = 1%)
- **force_swap_to_usdc**: Auto-swap to USDC on exit (default: true)

## Vault States

- **Idle**: Vault created, no active position
- **PositionOpen**: LP position active in range
- **ExitedToUSDC**: Exited and converted to USDC
- **Reentering**: Currently re-entering position

## Security Features

- PDA authority (no external keys can move funds)
- Reentrancy protection
- Keeper whitelist
- CPI program ID validation
- Slippage protection on all swaps
- Tick range validation

## Development Status

**Phase 1 - Current** ✅ **100% COMPLETE!**
- [x] Core program structure
- [x] State accounts (StrategyVault, VaultConfig)
- [x] All instructions implemented (10 total)
  - [x] create_vault, deposit, withdraw
  - [x] open_position_once
  - [x] decrease_liquidity_all
  - [x] collect_fees
  - [x] swap_all_to_usdc
  - [x] mark_exited_to_usdc
  - [x] reenter_with_liquidity
  - [x] set_params
- [x] Whirlpool CPI integration (COMPLETE)
  - [x] open_position_with_metadata
  - [x] increase_liquidity
  - [x] decrease_liquidity
  - [x] collect_fees
  - [x] Tick array derivation
- [x] Jupiter swap integration (COMPLETE)
  - [x] swap_with_route
  - [x] Remaining accounts handling
- [x] Keeper bot implementation (COMPLETE)
  - [x] IDL integration
  - [x] Pyth price monitoring
  - [x] TWAP calculation
  - [x] Auto-exit strategy
  - [x] Auto-reentry strategy
  - [x] Jupiter API integration
  - [x] Complete documentation
- [x] CLI scripts (COMPLETE)
  - [x] create-vault - Create new vaults
  - [x] deposit - Deposit tokens and receive shares
  - [x] withdraw - Burn shares and withdraw tokens
  - [x] view-vault - View vault state and balances
- [x] Test suite (COMPLETE)
  - [x] Anchor unit tests (10 tests)
  - [x] E2E tests (9 tests)
  - [x] Test utilities and helpers
  - [x] Mock data and fixtures

**Phase 2 - Future**
- Hyperliquid hedge integration
- Delta-neutral PnL tracking
- Funding rate arbitrage

**Phase 3 - Future**
- Web frontend
- Analytics dashboard
- Multi-strategy support

## Keeper Bot

The automated keeper bot monitors vault positions and executes auto-exit/reentry based on TWAP.

```bash
cd keeper

# Install dependencies
npm install

# Configure (copy and edit .env)
cp .env.example .env

# Run keeper
npm run dev

# Production
npm run build
npm start
```

See [keeper/README.md](keeper/README.md) and [keeper/IDL_INTEGRATION.md](keeper/IDL_INTEGRATION.md) for details.

## Testing

The project includes comprehensive test suites:

```bash
# Run all tests
anchor test

# Run with logs
anchor test -- --show-logs

# Run specific test file
anchor test tests/deltaneutrox-vault.ts

# Run E2E tests
anchor test tests/e2e/full-cycle.ts

# Test with Rust logs
RUST_LOG=debug anchor test
```

**Test Coverage**:
- ✅ 10 unit tests (vault creation, deposit, withdraw, params)
- ✅ 9 E2E tests (full lifecycle with multiple users)
- ✅ Error case testing
- ✅ Multi-user scenarios

See [tests/README.md](tests/README.md) for test documentation.

## CLI Usage

The CLI tools provide easy command-line interaction with vaults:

```bash
cd cli
npm install

# Configure
cp .env.example .env
# Edit .env with your wallet path and RPC URL

# Create vault
npm run create-vault -- \
  --pool <WHIRLPOOL_ID> \
  --token-a <TOKEN_A_MINT> \
  --usdc <USDC_MINT> \
  --tick-lower -20000 \
  --tick-upper 20000

# Deposit tokens
npm run deposit -- \
  --vault <VAULT_ID> \
  --amount-a 1.0 \
  --amount-usdc 100

# Withdraw
npm run withdraw -- \
  --vault <VAULT_ID> \
  --shares 1000

# View vault state
npm run view-vault -- --vault <VAULT_ID>
```

See [cli/README.md](cli/README.md) for complete documentation.

## Contributing

See [PLAN_DELTANEUTROX_FASE1.md](../PLAN_DELTANEUTROX_FASE1.md) for detailed implementation plan.

## License

MIT

## Disclaimer

This is experimental software. Use at your own risk. Always test thoroughly on devnet before mainnet deployment.
