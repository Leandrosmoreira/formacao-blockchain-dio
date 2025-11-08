use anchor_lang::prelude::*;

#[event]
pub struct VaultCreated {
    pub vault: Pubkey,
    pub authority: Pubkey,
    pub pool_id: Pubkey,
    pub token_a_mint: Pubkey,
    pub usdc_mint: Pubkey,
    pub tick_lower: i32,
    pub tick_upper: i32,
    pub timestamp: i64,
}

#[event]
pub struct Deposited {
    pub vault: Pubkey,
    pub user: Pubkey,
    pub amount_a: u64,
    pub amount_usdc: u64,
    pub shares_minted: u64,
    pub total_shares: u64,
    pub timestamp: i64,
}

#[event]
pub struct Withdrawn {
    pub vault: Pubkey,
    pub user: Pubkey,
    pub shares_burned: u64,
    pub amount_a: u64,
    pub amount_usdc: u64,
    pub total_shares: u64,
    pub timestamp: i64,
}

#[event]
pub struct PositionOpened {
    pub vault: Pubkey,
    pub position_key: Pubkey,
    pub liquidity: u128,
    pub amount_a: u64,
    pub amount_usdc: u64,
    pub tick_lower: i32,
    pub tick_upper: i32,
    pub timestamp: i64,
}

#[event]
pub struct LiquidityDecreased {
    pub vault: Pubkey,
    pub liquidity_removed: u128,
    pub amount_a: u64,
    pub amount_usdc: u64,
    pub timestamp: i64,
}

#[event]
pub struct FeesCollected {
    pub vault: Pubkey,
    pub amount_a: u64,
    pub amount_usdc: u64,
    pub timestamp: i64,
}

#[event]
pub struct SwappedToUSDC {
    pub vault: Pubkey,
    pub token_a_mint: Pubkey,
    pub amount_in: u64,
    pub amount_out: u64,
    pub timestamp: i64,
}

#[event]
pub struct AutoExitTriggered {
    pub vault: Pubkey,
    pub reason: String,
    pub trigger_price: u64,
    pub liquidity_removed: u128,
    pub timestamp: i64,
}

#[event]
pub struct ReentryOpened {
    pub vault: Pubkey,
    pub liquidity: u128,
    pub twap_price: u64,
    pub cooldown_elapsed_ms: u64,
    pub timestamp: i64,
}

#[event]
pub struct ParamsUpdated {
    pub vault: Pubkey,
    pub deadband_bps: u16,
    pub twap_window_secs: u32,
    pub cooldown_ms: u64,
    pub slippage_bps: u16,
    pub timestamp: i64,
}

#[event]
pub struct StatusChanged {
    pub vault: Pubkey,
    pub old_status: String,
    pub new_status: String,
    pub timestamp: i64,
}
