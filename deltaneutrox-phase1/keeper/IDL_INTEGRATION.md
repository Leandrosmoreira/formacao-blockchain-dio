# IDL Integration Documentation

This document explains the complete IDL integration for the DeltaNeutroX keeper bot.

## Overview

The keeper bot now fully integrates with the DeltaNeutroX Anchor program via its Interface Definition Language (IDL). This enables type-safe interactions with the on-chain program.

## Architecture

```
┌──────────────┐
│   idl.ts     │ ← TypeScript IDL definition
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ vault-manager.ts     │ ← Uses IDL to interact with program
│ - fetchVaultState()  │
│ - executeExit()      │
│ - executeReentry()   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│      pda.ts          │ ← PDA derivation helpers
│ - deriveVaultAuth()  │
│ - deriveTickArray()  │
└──────────────────────┘
```

## Key Files

### 1. `idl.ts` - Program IDL

The IDL defines the complete interface to the Anchor program:

```typescript
export type DeltaneutroxVault = {
  version: "0.1.0",
  name: "deltaneutrox_vault",
  instructions: [...],  // All program instructions
  accounts: [...],       // Account structures
  types: [...],          // Custom types
  errors: [...]          // Error codes
};
```

**Key Instructions:**
- `createVault` - Initialize a new vault
- `deposit` / `withdraw` - User operations
- `openPositionOnce` - Open Whirlpool position
- `decreaseLiquidityAll` - Exit position (100% liquidity)
- `collectFees` - Collect trading fees
- `swapAllToUsdc` - Swap token_a → USDC via Jupiter
- `markExitedToUsdc` - Mark vault as exited
- `reenterWithLiquidity` - Re-enter position
- `setParams` - Update vault parameters

**Account Structure:**
```typescript
{
  name: "strategyVault",
  type: {
    fields: [
      { name: "authority", type: "publicKey" },
      { name: "poolId", type: "publicKey" },
      { name: "positionKey", type: "publicKey" },
      { name: "status", type: { defined: "VaultStatus" } },
      { name: "config", type: { defined: "VaultConfig" } },
      // ... 19 total fields
    ]
  }
}
```

**Status Enum:**
```typescript
VaultStatus:
  - Idle          // Vault created, no position
  - PositionOpen  // Active LP position
  - ExitedToUSDC  // Exited, waiting for reentry
  - Reentering    // Re-entry in progress
```

### 2. `pda.ts` - PDA Helpers

Provides utilities for deriving Program Derived Addresses:

```typescript
// Vault authority PDA
// Seeds: ["vault_authority", vault_pubkey]
deriveVaultAuthority(vaultPubkey, programId): [PublicKey, number]

// Whirlpool tick array PDA
// Seeds: ["tick_array", whirlpool, start_tick_index]
deriveTickArray(whirlpool, startTickIndex): [PublicKey, number]

// Calculate tick array start index
getTickArrayStartIndex(tick, tickSpacing): number

// Associated token account
deriveAssociatedTokenAddress(owner, mint): PublicKey
```

**Constants:**
```typescript
VAULT_AUTHORITY_SEED = "vault_authority"
WHIRLPOOL_PROGRAM_ID = whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc
JUPITER_PROGRAM_ID   = JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4
```

### 3. `vault-manager.ts` - Program Interaction

The VaultManager class provides high-level methods for interacting with the vault:

#### Initialization

```typescript
constructor(config: KeeperConfig) {
  // 1. Load keeper keypair
  this.keeper = Keypair.fromSecretKey(...)

  // 2. Create Anchor provider
  const provider = new AnchorProvider(connection, wallet, {...})

  // 3. Initialize program with IDL
  this.program = new Program<DeltaneutroxVault>(IDL, programId, provider)

  // 4. Derive vault authority PDA
  [this.vaultAuthority, this.vaultAuthorityBump] =
    deriveVaultAuthority(vaultPubkey, programId)
}
```

#### Methods

**`fetchVaultState(): Promise<VaultState>`**

Fetches and deserializes the vault account:

```typescript
const vaultAccount = await this.program.account.strategyVault.fetch(vaultPubkey);

// Map Anchor enum to TypeScript enum
let status: VaultStatus;
if ('idle' in vaultAccount.status) status = VaultStatus.Idle;
else if ('positionOpen' in vaultAccount.status) status = VaultStatus.PositionOpen;
// ...

return {
  authority: vaultAccount.authority,
  poolId: vaultAccount.poolId,
  status,
  config: vaultAccount.config,
  // ... all fields
};
```

**`executeExit(twapPrice: number): Promise<string>`**

Executes the full exit sequence:

```typescript
async executeExit(twapPrice: number): Promise<string> {
  // 1. Fetch vault state
  const state = await this.fetchVaultState();

  // 2. Validate state (PositionOpen, not in progress)
  if (state.status !== VaultStatus.PositionOpen) throw error;

  // 3. Fetch whirlpool data (token vaults, tick spacing)
  const whirlpoolData = await this.fetchWhirlpoolData(state.poolId);

  // 4. Derive tick arrays
  const tickArrayLower = deriveTickArray(poolId, lowerStartIndex);
  const tickArrayUpper = deriveTickArray(poolId, upperStartIndex);

  // 5. Execute instructions in sequence:

  // Step 1: Decrease liquidity to 100%
  await this.program.methods
    .decreaseLiquidityAll()
    .accounts({
      vault, vaultAuthority, whirlpoolProgram,
      whirlpool, position, positionTokenAccount,
      vaultTokenA, vaultUsdc, tokenVaultA, tokenVaultB,
      tickArrayLower, tickArrayUpper, keeper, tokenProgram
    })
    .rpc();

  // Step 2: Collect fees
  await this.program.methods.collectFees().accounts({...}).rpc();

  // Step 3: Swap to USDC (if configured)
  if (state.config.forceSwapToUsdc) {
    await this.executeSwapToUSDC(state);
  }

  // Step 4: Mark as exited
  await this.program.methods
    .markExitedToUsdc()
    .accounts({ vault, keeper, clock })
    .rpc();

  return txSignature;
}
```

**`executeReentry(twapPrice: number, targetLiquidity: BN): Promise<string>`**

Executes the reentry sequence:

```typescript
async executeReentry(twapPrice: number, targetLiquidity: BN): Promise<string> {
  // 1. Fetch and validate state (ExitedToUSDC, cooldown passed)
  const state = await this.fetchVaultState();
  const { canReenter } = await this.canReenter();
  if (!canReenter) throw error;

  // 2. Derive required accounts
  const whirlpoolData = await this.fetchWhirlpoolData(state.poolId);
  const tickArrayLower = deriveTickArray(...);
  const tickArrayUpper = deriveTickArray(...);

  // 3. Execute reentry instruction
  await this.program.methods
    .reenterWithLiquidity(targetLiquidity)
    .accounts({
      vault, vaultAuthority, whirlpoolProgram,
      whirlpool, position, positionTokenAccount,
      vaultTokenA, vaultUsdc, tokenVaultA, tokenVaultB,
      tickArrayLower, tickArrayUpper, keeper, clock, tokenProgram
    })
    .rpc();

  return txSignature;
}
```

**`executeSwapToUSDC(state: VaultState): Promise<string>`**

Swaps token_a to USDC via Jupiter:

```typescript
private async executeSwapToUSDC(state: VaultState): Promise<string> {
  // 1. Get token_a balance
  const tokenAAccount = await connection.getTokenAccountBalance(vaultTokenA);

  // 2. Get Jupiter quote
  const quote = await jupiterClient.getQuote(
    tokenAMint, usdcMint, amount, slippageBps
  );

  // 3. Get swap instructions
  const swapInstructions = await jupiterClient.getSwapInstructions(
    quote, vaultAuthority
  );

  // 4. Build remaining accounts from Jupiter
  const remainingAccounts = swapInstructions.swapInstruction.accounts.map(...);

  // 5. Execute swap instruction
  await this.program.methods
    .swapAllToUsdc()
    .accounts({ vault, vaultAuthority, jupiterProgram, ... })
    .remainingAccounts(remainingAccounts)
    .rpc();
}
```

## Account Derivation

### Vault Authority

The vault authority is a PDA that signs on behalf of the vault:

```typescript
Seeds: ["vault_authority", vault_pubkey]
Program: DeltaNeutroX Program ID
```

Used for:
- Token transfers from vault token accounts
- Signing Whirlpool CPIs
- Signing Jupiter swap CPIs

### Tick Arrays

Whirlpool organizes ticks into arrays of 88 ticks each:

```typescript
function getTickArrayStartIndex(tick: number, tickSpacing: number): number {
  const ticksPerArray = tickSpacing * 88;
  const arrayIndex = Math.floor(tick / ticksPerArray);
  return arrayIndex * ticksPerArray;
}

// Example: tick = 1000, tickSpacing = 64
// ticksPerArray = 64 * 88 = 5632
// arrayIndex = floor(1000 / 5632) = 0
// startIndex = 0 * 5632 = 0
```

Both lower and upper tick arrays are required for liquidity operations.

### Position Token Account

The position NFT is held in an ATA owned by the vault authority:

```typescript
const positionTokenAccount = deriveAssociatedTokenAddress(
  vaultAuthority,
  positionKey  // The position mint (NFT)
);
```

## Integration with Strategy Engine

The `StrategyEngine` uses `VaultManager` methods:

```typescript
// In strategy.ts
private async handlePositionOpenState(...) {
  const isOutsideDeadband = Math.abs(deviation) > deadbandBps;

  if (isOutsideDeadband) {
    // Trigger exit via VaultManager
    const txSig = await this.vaultManager.executeExit(twap);
    console.log(`Exit executed: ${txSig}`);
  }
}

private async handleExitedState(...) {
  const { canReenter } = await this.vaultManager.canReenter();
  const isWithinDeadband = Math.abs(deviation) <= deadbandBps;

  if (canReenter && isWithinDeadband) {
    // Trigger reentry via VaultManager
    const targetLiquidity = calculateLiquidity(...);
    const txSig = await this.vaultManager.executeReentry(twap, targetLiquidity);
    console.log(`Reentry executed: ${txSig}`);
  }
}
```

## Error Handling

The IDL includes 20 custom error codes (6000-6019):

```typescript
6000: InvalidVaultStatus       - Wrong status for operation
6001: OperationInProgress      - Reentrancy protection triggered
6002: UnauthorizedKeeper       - Keeper not authorized
6003: CooldownNotMet           - Reentry too soon
6004: InvalidTickRange         - Bad tick configuration
6005: SlippageExceeded         - Slippage too high
// ... and 14 more
```

Errors are automatically decoded by Anchor:

```typescript
try {
  await this.program.methods.reenterWithLiquidity(...).rpc();
} catch (error) {
  // Anchor automatically translates error code to message
  // e.g., "Error Code: CooldownNotMet. Error Message: Cooldown period not met - wait before re-entry"
  console.error(error);
}
```

## Whirlpool Data Parsing

The `fetchWhirlpoolData()` method parses raw Whirlpool account data:

```typescript
// Whirlpool account layout (simplified):
// Offset | Size | Field
// -------|------|-------------------
// 0      | 8    | discriminator
// 8      | 32   | whirlpools_config
// 40     | 1    | whirlpool_bump
// 41     | 2    | tick_spacing
// ...    | ...  | ...
// 101    | 32   | token_mint_a
// 133    | 32   | token_vault_a
// 165    | 16   | fee_growth_global_a
// 181    | 32   | token_mint_b
// 213    | 32   | token_vault_b

const data = accountInfo.data;
const tokenMintA = new PublicKey(data.slice(101, 133));
const tokenVaultA = new PublicKey(data.slice(133, 165));
const tokenMintB = new PublicKey(data.slice(181, 213));
const tokenVaultB = new PublicKey(data.slice(213, 245));
const tickSpacing = data.readUInt16LE(41);
```

## Testing the Integration

### 1. Setup

```bash
# Create keeper keypair
mkdir -p ../keypairs
solana-keygen new -o ../keypairs/keeper.json

# Fund keeper
solana airdrop 2 $(solana-keygen pubkey ../keypairs/keeper.json) --url devnet

# Configure .env
cp .env.example .env
# Edit .env with your vault pubkey
```

### 2. Test Vault State Fetch

```typescript
const vaultManager = new VaultManager(config);
const state = await vaultManager.fetchVaultState();

console.log('Vault Status:', VaultStatus[state.status]);
console.log('Position Key:', state.positionKey.toString());
console.log('Tick Range:', state.tickLower, '-', state.tickUpper);
console.log('Cooldown:', state.config.cooldownMs.toNumber(), 'ms');
```

### 3. Test Exit (when PositionOpen)

```typescript
const canExit = await vaultManager.canExit();
if (canExit) {
  const txSig = await vaultManager.executeExit(95.50);
  console.log('Exit TX:', txSig);
}
```

### 4. Test Reentry (when ExitedToUSDC)

```typescript
const { canReenter, cooldownRemaining } = await vaultManager.canReenter();
console.log('Can reenter:', canReenter);
console.log('Cooldown remaining:', cooldownRemaining, 'ms');

if (canReenter) {
  const targetLiquidity = new BN(1000000);
  const txSig = await vaultManager.executeReentry(95.25, targetLiquidity);
  console.log('Reentry TX:', txSig);
}
```

## Production Considerations

1. **RPC Rate Limits**: Use premium RPC (Helius, QuickNode, Triton) for production

2. **Transaction Confirmation**: Currently using 'confirmed' commitment. Consider 'finalized' for critical operations.

3. **Compute Budget**: Add compute budget instructions for complex transactions:
   ```typescript
   .preInstructions([
     ComputeBudgetProgram.setComputeUnitLimit({ units: 300_000 }),
     ComputeBudgetProgram.setComputeUnitPrice({ microLamports: 1 })
   ])
   ```

4. **Priority Fees**: Use priority fees during high congestion

5. **Whirlpool SDK**: Consider using `@orca-so/whirlpools-sdk` instead of manual parsing

6. **Error Recovery**: Implement retry logic for transient RPC errors

7. **Monitoring**: Add metrics export (Prometheus) and alerting

## Dependencies

```json
{
  "@coral-xyz/anchor": "^0.30.1",
  "@solana/web3.js": "^1.95.0",
  "@solana/spl-token": "^0.4.0",
  "@pythnetwork/client": "^2.21.0",
  "axios": "^1.6.7"
}
```

## Conclusion

The IDL integration provides:
- ✅ Type-safe program interactions
- ✅ Automatic account serialization/deserialization
- ✅ Error code translation
- ✅ Complete vault state access
- ✅ Full exit/reentry automation

The keeper bot is now ready for devnet testing and can be deployed once the Anchor program is deployed.
