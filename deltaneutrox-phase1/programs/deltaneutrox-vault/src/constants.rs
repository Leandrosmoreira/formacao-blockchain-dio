use anchor_lang::prelude::*;

/// Seed for vault authority PDA
pub const VAULT_AUTHORITY_SEED: &[u8] = b"vault_authority";

/// Seed for shares mint PDA
pub const SHARES_MINT_SEED: &[u8] = b"shares_mint";

/// Maximum slippage in basis points (10% = 1000 bps)
pub const MAX_SLIPPAGE_BPS: u16 = 1000;

/// Maximum deadband in basis points (5% = 500 bps)
pub const MAX_DEADBAND_BPS: u16 = 500;

/// Minimum cooldown in milliseconds (1 minute)
pub const MIN_COOLDOWN_MS: u64 = 60_000;

/// Maximum cooldown in milliseconds (30 minutes)
pub const MAX_COOLDOWN_MS: u64 = 1_800_000;

/// Minimum TWAP window in seconds (10 seconds)
pub const MIN_TWAP_WINDOW_SECS: u32 = 10;

/// Maximum TWAP window in seconds (5 minutes)
pub const MAX_TWAP_WINDOW_SECS: u32 = 300;

/// Whirlpool program ID
pub const WHIRLPOOL_PROGRAM_ID: Pubkey = anchor_lang::solana_program::pubkey!(
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
);

/// Jupiter V6 program ID
pub const JUPITER_PROGRAM_ID: Pubkey = anchor_lang::solana_program::pubkey!(
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
);

/// USDC mint address (devnet - replace for mainnet)
pub const USDC_MINT_DEVNET: Pubkey = anchor_lang::solana_program::pubkey!(
    "Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr"
);

/// USDC mint address (mainnet)
pub const USDC_MINT_MAINNET: Pubkey = anchor_lang::solana_program::pubkey!(
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
);
