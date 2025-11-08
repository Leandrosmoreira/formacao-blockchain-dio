# DeltaNeutroX Keeper Bot

Automated keeper bot for managing delta-neutral vault positions on Solana with Orca Whirlpool integration.

## Features

- **TWAP-based Price Monitoring**: Uses Pyth Network price feeds with time-weighted average price calculation
- **Auto-Exit**: Automatically exits positions when price moves outside configured range
- **Auto-Reentry**: Intelligently re-enters positions based on TWAP with hysteresis (deadband + cooldown)
- **Jupiter Integration**: Optimal token swaps via Jupiter Aggregator V6
- **Robust Error Handling**: Automatic retry logic and graceful error recovery

## Architecture

```
┌─────────────────┐
│  Pyth Network   │ (Price Feeds)
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Price Monitor   │────▶│ TWAP Calculator  │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Strategy Engine      │
         │  - Exit Logic         │
         │  - Reentry Logic      │
         │  - Hysteresis Control │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│  Vault Manager  │     │  Jupiter Client  │
│  (Anchor CPIs)  │     │  (Swap Quotes)   │
└─────────────────┘     └──────────────────┘
```

## Installation

```bash
cd deltaneutrox-phase1/keeper
npm install
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and configure:

```bash
# Solana RPC (use premium RPC for production)
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_WSS_URL=wss://api.devnet.solana.com

# Keeper wallet keypair
KEEPER_KEYPAIR_PATH=../keypairs/keeper.json

# Vault to manage
VAULT_PUBKEY=<your-vault-pubkey>
PROGRAM_ID=Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS

# Pyth price feed (SOL/USD on devnet)
PYTH_PRICE_FEED_ID=J83w4HKfqxwcq3BEMMkPFSppX3gqekLyLJBexebFVkix

# Strategy parameters
DEADBAND_BPS=50              # 0.5% hysteresis band
TWAP_WINDOW_SECS=60          # 60 seconds TWAP window
COOLDOWN_MS=180000           # 3 minutes cooldown
CHECK_INTERVAL_MS=5000       # Check every 5 seconds
```

3. Create a keeper keypair:
```bash
mkdir -p ../keypairs
solana-keygen new -o ../keypairs/keeper.json
```

4. Fund the keeper wallet:
```bash
solana airdrop 2 $(solana-keygen pubkey ../keypairs/keeper.json) --url devnet
```

## Usage

### Development Mode
```bash
npm run dev
```

### Production Mode
```bash
npm run build
npm start
```

## Strategy Logic

### Exit Condition
The keeper exits the position when:
1. Vault status is `PositionOpen`
2. Current price deviates from TWAP by more than `DEADBAND_BPS`

### Reentry Condition
The keeper re-enters the position when:
1. Vault status is `ExitedToUSDC`
2. Cooldown period has elapsed (at least `COOLDOWN_MS` since last exit)
3. Current price is back within `DEADBAND_BPS` of TWAP

### Hysteresis Parameters

**Deadband (DEADBAND_BPS)**:
- Prevents rapid exit/reentry oscillations
- Typical values: 25-100 bps (0.25% - 1%)
- Lower = more responsive but more transactions
- Higher = less responsive but fewer transactions

**Cooldown (COOLDOWN_MS)**:
- Minimum time between exit and reentry
- Prevents immediate reentry after exit
- Typical values: 60000-600000 ms (1-10 minutes)
- Allows price to stabilize after volatility

**TWAP Window (TWAP_WINDOW_SECS)**:
- Time window for price averaging
- Filters out short-term price noise
- Typical values: 30-300 seconds (0.5-5 minutes)
- Longer = smoother but slower to react

## File Structure

```
keeper/
├── src/
│   ├── index.ts           # Main entry point
│   ├── config.ts          # Configuration loader
│   ├── pyth-monitor.ts    # Pyth price monitoring
│   ├── twap.ts            # TWAP calculation
│   ├── vault-manager.ts   # Vault interaction (Anchor)
│   ├── jupiter-api.ts     # Jupiter API client
│   └── strategy.ts        # Strategy engine logic
├── package.json
├── tsconfig.json
├── .env.example
└── README.md
```

## Monitoring

The keeper outputs detailed logs:

```
[2024-01-15T10:30:45.123Z] Status: PositionOpen | Price: $95.1234 | TWAP: $95.0000 | Deviation: +12.34 bps
```

Key metrics:
- **Status**: Current vault state (Idle, PositionOpen, ExitedToUSDC, Reentering)
- **Price**: Latest Pyth price
- **TWAP**: Time-weighted average price
- **Deviation**: Price deviation from TWAP in basis points

## Error Handling

The keeper includes robust error handling:
- Automatic retry on transient RPC errors
- Graceful shutdown on consecutive failures (10 errors)
- Validation of all configuration parameters
- Safe handling of missing price data

## Security Considerations

1. **Keeper Keypair**: Keep your keeper keypair secure. It needs authority to execute vault operations.

2. **RPC Limits**: Use a premium RPC provider for production to avoid rate limiting.

3. **Transaction Simulation**: Always test on devnet first.

4. **Monitoring**: Set up alerts for keeper downtime or consecutive errors.

## Troubleshooting

### "Price feed data not available"
- Check that the Pyth price feed ID is correct
- Verify RPC connection is working
- Ensure price feed is active on the target network

### "UnauthorizedKeeper" error
- Verify keeper keypair matches the vault's `keeper_authority`
- Check that you're using the correct vault pubkey

### "CooldownNotMet" error
- Wait for the cooldown period to elapse
- Check `COOLDOWN_MS` configuration

### High consecutive errors
- Check RPC connection and rate limits
- Verify account states are valid
- Review Solana cluster status

## Advanced Configuration

### Using Premium RPC (Production)

For production, use a premium RPC provider:

```bash
# Helius (recommended)
SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY

# Or QuickNode
SOLANA_RPC_URL=https://example.solana-mainnet.quiknode.pro/YOUR_KEY/

# Or Triton
SOLANA_RPC_URL=https://example.rpcpool.com/YOUR_KEY
```

### Mainnet Price Feeds

For mainnet, use the appropriate Pyth price feed:
```bash
# SOL/USD on mainnet
PYTH_PRICE_FEED_ID=H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG
```

See https://pyth.network/developers/price-feed-ids for all available feeds.

## TODO / Future Improvements

- [ ] Add IDL loading for proper Anchor program interaction
- [ ] Implement remaining accounts building for Jupiter swaps
- [ ] Add Telegram/Discord notifications for actions
- [ ] Implement metrics export (Prometheus/Grafana)
- [ ] Add backtesting mode with historical data
- [ ] Support multiple vaults from single keeper
- [ ] Add web dashboard for monitoring

## License

MIT
