# CPI Integration Guide - DeltaNeutroX Phase 1

Este documento explica como as Cross-Program Invocations (CPIs) foram implementadas para integração com Orca Whirlpool e Jupiter Aggregator.

---

## Whirlpool CPI Implementation

### Funções Implementadas

#### 1. `open_position_with_metadata`

Abre uma nova posição LP no pool Whirlpool.

**Parâmetros:**
- `tick_lower_index`: Tick inferior do range
- `tick_upper_index`: Tick superior do range
- `signer_seeds`: Seeds da PDA (vault_authority)

**Accounts Necessárias:**
- `whirlpool_program`: Programa Whirlpool
- `funder`: Quem paga pela criação
- `owner`: Dono da posição (vault_authority PDA)
- `position`: Conta da posição (PDA)
- `position_mint`: NFT da posição
- `position_token_account`: ATA do NFT
- `whirlpool`: Pool onde abrir posição
- `token_program`, `system_program`, `rent`
- `associated_token_program`
- `metadata_program`: Metaplex Token Metadata
- `metadata_update_auth`: Autoridade de update

**Discriminator:** `0x7d4f355c5c6f0c8e`

---

#### 2. `increase_liquidity`

Adiciona liquidez a uma posição existente.

**Parâmetros:**
- `liquidity_amount`: Quantidade de liquidez (u128)
- `token_max_a`: Máximo de token A a depositar
- `token_max_b`: Máximo de token B (USDC) a depositar
- `signer_seeds`: Seeds da PDA

**Accounts Necessárias:**
- `whirlpool_program`
- `whirlpool`: Pool
- `token_program`
- `position_authority`: PDA (signer)
- `position`: Posição criada
- `position_token_account`: ATA do NFT
- `token_owner_account_a`: Vault's token A account
- `token_owner_account_b`: Vault's USDC account
- `token_vault_a`: Token A vault do pool
- `token_vault_b`: USDC vault do pool
- `tick_array_lower`: Tick array do tick inferior
- `tick_array_upper`: Tick array do tick superior

**Discriminator:** `0x2e889c0a845c6c4e`

**Tick Arrays:**
- Use `get_tick_array_start_index()` para calcular o índice
- Use `derive_tick_array_pda()` para derivar a PDA

---

#### 3. `decrease_liquidity`

Remove liquidez de uma posição.

**Parâmetros:**
- `liquidity_amount`: Quantidade a remover (u128, passar 100% para exit total)
- `token_min_a`: Mínimo de token A a receber (slippage)
- `token_min_b`: Mínimo de USDC a receber (slippage)
- `signer_seeds`: Seeds da PDA

**Accounts:** Mesmas de `increase_liquidity`

**Discriminator:** `0xa02a19fbdc9ba59d`

---

#### 4. `collect_fees`

Coleta fees acumulados da posição.

**Parâmetros:**
- `signer_seeds`: Seeds da PDA

**Accounts:**
- `whirlpool_program`
- `whirlpool`
- `position_authority`: PDA (signer)
- `position`
- `position_token_account`
- `token_owner_account_a`: Destino dos fees em token A
- `token_vault_a`: Vault A do pool
- `token_owner_account_b`: Destino dos fees em USDC
- `token_vault_b`: Vault B do pool
- `token_program`

**Discriminator:** `0xa59b8a4823976210`

---

#### 5. `close_position`

Fecha uma posição (deve ter liquidez = 0).

**Parâmetros:**
- `signer_seeds`: Seeds da PDA

**Accounts:**
- `whirlpool_program`
- `position_authority`: PDA (signer)
- `receiver`: Quem recebe o rent da posição
- `position`
- `position_mint`
- `position_token_account`
- `token_program`

**Discriminator:** `0x7b4e163a5cd68a91`

---

### Helpers Whirlpool

```rust
// Calcular tick array start index
let tick_spacing = 64; // ou 128, depende do pool
let start_index_lower = get_tick_array_start_index(tick_lower, tick_spacing);
let start_index_upper = get_tick_array_start_index(tick_upper, tick_spacing);

// Derivar tick array PDAs
let (tick_array_lower, _bump) = derive_tick_array_pda(&whirlpool_key, start_index_lower);
let (tick_array_upper, _bump) = derive_tick_array_pda(&whirlpool_key, start_index_upper);
```

---

## Jupiter CPI Implementation

### Funções Implementadas

#### 1. `swap_with_route`

Executa swap usando rota do Jupiter API.

**Parâmetros:**
- `amount_in`: Quantidade de input (u64)
- `minimum_amount_out`: Mínimo de output (u64)
- `platform_fee_bps`: Fee da plataforma (u8, 0-100)
- `remaining_accounts`: Contas da rota (dinâmico)
- `signer_seeds`: Seeds da PDA

**Accounts Fixas:**
- `jupiter_program`: Jupiter V6
- `token_program`
- `user_transfer_authority`: PDA (signer)
- `user_source_token_account`: Source (vault token A)
- `user_destination_token_account`: Destination (vault USDC)
- `destination_token_account`: Same as above
- `source_mint`: Token A mint
- `destination_mint`: USDC mint
- `platform_fee_account`: Vault USDC (fees vão para o vault)

**Remaining Accounts:**
- Obtidas via Jupiter API `/quote` endpoint
- Passadas dinamicamente pelo keeper

**Discriminator:** `0xe445a52e51cb9a1d`

**Exemplo de uso:**

```typescript
// 1. Keeper obtém quote do Jupiter API
const quote = await fetch(
  `https://quote-api.jup.ag/v6/quote?inputMint=${tokenA}&outputMint=${USDC}&amount=${amount}&slippageBps=100`
).then(r => r.json());

// 2. Obtém instruções de swap
const swapIx = await fetch('https://quote-api.jup.ag/v6/swap-instructions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    quoteResponse: quote,
    userPublicKey: vaultAuthority.toString(),
  })
}).then(r => r.json());

// 3. Passa as contas como remainingAccounts no Anchor
await program.methods
  .swapAllToUsdc()
  .accounts({ /* ... */ })
  .remainingAccounts(swapIx.addressLookupTableAddresses)
  .rpc();
```

---

#### 2. `swap_exact_in`

Swap simplificado para pares diretos (devnet testing).

**Parâmetros:**
- `amount_in`: Quantidade de input
- `minimum_amount_out`: Mínimo de output
- `signer_seeds`: Seeds da PDA

**Accounts:**
- `jupiter_program`
- `token_program`
- `user_transfer_authority`: PDA
- `user_source_token_account`
- `user_destination_token_account`
- `swap_program`: Programa do pool (Orca, Raydium, etc)
- `swap_state`: Estado do pool
- `authority`: Autoridade do pool
- `source_vault`: Vault source do pool
- `destination_vault`: Vault destination do pool

---

### Helpers Jupiter

```rust
// Calcular minimum_amount_out com slippage
let slippage_bps = 100; // 1%
let min_out = calculate_min_amount_out(expected_out, slippage_bps);

// Estimar output (para testing, use Jupiter API em produção)
let estimated = estimate_swap_output(
    amount_in,
    pool_reserve_in,
    pool_reserve_out,
    pool_fee_bps
);
```

---

## Fluxo de Exit Completo

### Sequência de Instruções

```rust
// 1. Decrease liquidity 100%
program.methods
    .decreaseLiquidityAll()
    .accounts({ /* whirlpool accounts */ })
    .rpc();

// 2. Collect fees
program.methods
    .collectFees()
    .accounts({ /* whirlpool accounts */ })
    .rpc();

// 3. Swap token A -> USDC
program.methods
    .swapAllToUsdc()
    .accounts({ /* jupiter accounts */ })
    .remainingAccounts(jupiterRoute)
    .rpc();

// 4. Mark vault as exited
program.methods
    .markExitedToUsdc()
    .accounts({ /* vault */ })
    .rpc();
```

---

## Fluxo de Re-entry Completo

### Sequência de Instruções

```rust
// 1. (Opcional) Swap USDC -> token A para balancear
program.methods
    .swapForReentry()
    .accounts({ /* jupiter accounts */ })
    .remainingAccounts(jupiterRoute)
    .rpc();

// 2. Re-enter position
program.methods
    .reenterWithLiquidity(targetLiquidity)
    .accounts({ /* whirlpool accounts */ })
    .rpc();
```

---

## Derivação de PDAs

### Vault Authority

```rust
seeds = [b"vault_authority", vault.key().as_ref()]
```

### Whirlpool Position

```rust
seeds = [b"position", position_mint.key().as_ref()]
program_id = WHIRLPOOL_PROGRAM_ID
```

### Tick Arrays

```rust
seeds = [b"tick_array", whirlpool.key().as_ref(), start_tick.to_string().as_bytes()]
program_id = WHIRLPOOL_PROGRAM_ID
```

---

## Segurança e Validações

### Whirlpool

- ✅ Validar program_id = `whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc`
- ✅ Validar pool_id contra whitelist
- ✅ Validar tick_lower < tick_upper
- ✅ Aplicar slippage em token_max e token_min
- ✅ Usar PDA como signer (invoke_signed)

### Jupiter

- ✅ Validar program_id = `JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4`
- ✅ Aplicar slippage em minimum_amount_out
- ✅ Validar mints (source = token_a, dest = usdc)
- ✅ Usar PDA como signer
- ✅ Validar remaining_accounts não vazios

---

## Testes em Devnet

### 1. Encontrar Pool Whirlpool

```bash
# SOL/USDC pool no devnet
POOL_ID="HJPjoWUrhoZzkNfRpHuieeFk9WcZWjwy6PBjZ81ngndJ"
```

### 2. Obter Quote do Jupiter

```bash
curl "https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&amount=1000000&slippageBps=100"
```

### 3. Executar Swap

```typescript
const tx = await program.methods
  .swapAllToUsdc()
  .accounts({
    vault: vaultPDA,
    vaultAuthority: authorityPDA,
    vaultTokenA: vaultTokenAAccount,
    vaultUsdc: vaultUsdcAccount,
    tokenAMint: SOL_MINT,
    usdcMint: USDC_MINT,
    jupiterProgram: JUPITER_PROGRAM_ID,
    tokenProgram: TOKEN_PROGRAM_ID,
    keeper: keeper.publicKey,
  })
  .remainingAccounts(jupiterAccounts)
  .rpc();
```

---

## Troubleshooting

### Erro: "Invalid instruction data"

- Verificar discriminators estão corretos
- Verificar serialização de parâmetros (little-endian)

### Erro: "Account not provided"

- Verificar todas as accounts necessárias foram passadas
- Para Jupiter, verificar remaining_accounts do quote

### Erro: "Invalid program id"

- Verificar program_id constraints
- Usar constantes WHIRLPOOL_PROGRAM_ID e JUPITER_PROGRAM_ID

### Erro: "Slippage tolerance exceeded"

- Aumentar slippage_bps
- Para Whirlpool: ajustar token_max e token_min
- Para Jupiter: ajustar minimum_amount_out

---

## Próximos Passos

- [ ] Implementar open_position completo com Whirlpool
- [ ] Implementar decrease_liquidity com Whirlpool
- [ ] Implementar collect_fees com Whirlpool
- [ ] Testar swap Jupiter em devnet
- [ ] Implementar keeper com integração Jupiter API
- [ ] Testes E2E completos

---

## Referências

- [Orca Whirlpool SDK](https://github.com/orca-so/whirlpools)
- [Jupiter V6 Documentation](https://station.jup.ag/docs/apis/swap-api)
- [Anchor CPI Guide](https://www.anchor-lang.com/docs/cross-program-invocations)
- [Solana CPI Deep Dive](https://solanacookbook.com/references/programs.html#how-to-do-cross-program-invocation)
