# Tests

Test suite for DeltaNeutroX Phase 1 vault program.

## Status

✅ **Implemented** - Ready to run

## Test Structure

```
tests/
├── deltaneutrox-vault.ts     # Main Anchor tests ✅
├── utils/
│   └── setup.ts               # Test fixtures and helpers ✅
└── e2e/
    └── full-cycle.ts          # End-to-end test ✅
```

## Implemented Tests

### Unit Tests (Anchor)

**deltaneutrox-vault.ts**

1. **Vault Creation**
   - ✓ Creates vault with correct parameters
   - ✓ Initializes shares mint
   - ✓ Creates token accounts
   - ✓ Sets keeper authority
   - ✗ Fails with invalid tick range
   - ✗ Fails with invalid slippage

2. **Deposit**
   - ✓ Deposits tokens and mints shares
   - ✓ Calculates correct share amount
   - ✓ Updates total_deposits
   - ✗ Fails when operation in progress
   - ✗ Fails with zero amount

3. **Withdraw**
   - ✓ Burns shares and withdraws tokens
   - ✓ Calculates correct token amounts (pro-rata)
   - ✓ Updates total_withdrawals
   - ✗ Fails when insufficient shares
   - ✗ Fails when operation in progress

4. **Open Position**
   - ✓ Opens Whirlpool position
   - ✓ Mints position NFT
   - ✓ Adds initial liquidity
   - ✓ Updates vault status to PositionOpen
   - ✗ Fails when already have position
   - ✗ Fails when unauthorized keeper

5. **Decrease Liquidity**
   - ✓ Decreases 100% of liquidity
   - ✓ Returns tokens to vault
   - ✓ Maintains position NFT
   - ✗ Fails when no active position
   - ✗ Fails when unauthorized keeper

6. **Collect Fees**
   - ✓ Collects fees from position
   - ✓ Emits correct event with amounts
   - ✗ Fails when no active position

7. **Swap to USDC**
   - ✓ Swaps token_a to USDC via Jupiter
   - ✓ Respects slippage settings
   - ✓ Emits swap event
   - ✗ Fails with high slippage

8. **Mark Exited**
   - ✓ Marks vault as ExitedToUSDC
   - ✓ Sets last_exit_timestamp
   - ✓ Clears operation_in_progress
   - ✗ Fails when not authorized

9. **Reentry**
   - ✓ Increases liquidity on existing position
   - ✓ Updates status to PositionOpen
   - ✗ Fails when cooldown not met
   - ✗ Fails when not in ExitedToUSDC state

10. **Set Params**
    - ✓ Updates configuration parameters
    - ✓ Validates new parameters
    - ✗ Fails when invalid values
    - ✗ Fails when unauthorized

### E2E Tests

**e2e/full-cycle.ts**

1. **Complete Lifecycle Test**
   ```typescript
   // 1. Setup
   - Create vault
   - Setup Whirlpool pool mock
   - Fund user accounts

   // 2. Initial deposit
   - User deposits SOL + USDC
   - Receives vault shares

   // 3. Position management
   - Keeper opens position
   - Position accumulates fees
   - Price moves outside range

   // 4. Auto-exit
   - Keeper decreases liquidity
   - Keeper collects fees
   - Keeper swaps to USDC
   - Vault marked as exited

   // 5. Wait cooldown
   - Time passes (cooldown period)
   - Price returns to range

   // 6. Auto-reentry
   - Keeper re-enters position
   - Liquidity added back

   // 7. User withdrawal
   - User burns shares
   - Receives pro-rata tokens
   - Vault balances correct
   ```

2. **Multiple Users Test**
   - Multiple users deposit
   - Shares calculated correctly
   - Withdrawals pro-rata correct
   - Fee distribution fair

3. **Error Recovery Test**
   - Handle failed transactions
   - Reentrancy protection works
   - Cooldown enforcement works

## Test Helpers

**utils/setup.ts**
```typescript
export async function setupVault(
  provider: AnchorProvider,
  poolId: PublicKey,
  tickLower: number,
  tickUpper: number
): Promise<VaultAccounts>

export async function fundUser(
  provider: AnchorProvider,
  user: PublicKey,
  amountSol: number,
  amountUsdc: number
): Promise<void>

export async function createWhirlpoolMock(): Promise<PublicKey>
```

**utils/vault-helpers.ts**
```typescript
export async function deposit(
  program: Program,
  vault: PublicKey,
  user: Keypair,
  amountA: number,
  amountUsdc: number
): Promise<string>

export async function withdraw(
  program: Program,
  vault: PublicKey,
  user: Keypair,
  shares: number
): Promise<string>

export async function getVaultState(
  program: Program,
  vault: PublicKey
): Promise<VaultState>
```

## Running Tests

```bash
# Run all tests
anchor test

# Run specific test file
anchor test -- tests/deltaneutrox-vault.ts

# Run with logs
RUST_LOG=debug anchor test

# Run E2E only
anchor test -- tests/e2e/

# Run with coverage (requires cargo-llvm-cov)
cargo llvm-cov --html
```

## Test Configuration

**Anchor.toml**
```toml
[test]
# Use local validator with cloned programs
startup_wait = 5000

[[test.validator.clone]]
address = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"  # Whirlpool

[[test.validator.clone]]
address = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"  # Jupiter
```

## Mock Data

For testing without real Whirlpool/Jupiter:

1. **Whirlpool Mock**
   - Simulates pool state
   - Mocks tick arrays
   - Returns deterministic results

2. **Jupiter Mock**
   - Returns fixed swap quotes
   - Simulates successful swaps

## Coverage Goals

- **Instruction coverage**: 100%
- **Branch coverage**: >90%
- **Error path coverage**: 100%
- **Integration coverage**: >80%

## Implementation Priority

1. **HIGH**: Core instruction tests (create, deposit, withdraw)
2. **HIGH**: Position management tests (open, decrease, collect)
3. **MEDIUM**: Exit/reentry flow tests
4. **MEDIUM**: E2E full cycle test
5. **LOW**: Error path edge cases
6. **LOW**: Performance/stress tests

## Contributing

When implementing tests:

1. Use descriptive test names
2. Test both success and failure cases
3. Clean up accounts after tests
4. Use test fixtures for common setup
5. Document complex test scenarios
6. Keep tests isolated (no shared state)

## References

- [Anchor Testing Guide](https://www.anchor-lang.com/docs/testing)
- [Solana Program Testing](https://docs.solana.com/developing/test-validator)
- [keeper/src/](../keeper/src/) - For IDL and account structures
