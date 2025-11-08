use anchor_lang::prelude::*;

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Default)]
pub struct VaultConfig {
    /// Deadband in basis points (e.g., 50 = 0.5%)
    /// Used for hysteresis in re-entry logic
    pub deadband_bps: u16,

    /// TWAP window in seconds (e.g., 60 = 1 minute)
    pub twap_window_secs: u32,

    /// Cooldown period in milliseconds before re-entry allowed
    /// (e.g., 180000 = 3 minutes)
    pub cooldown_ms: u64,

    /// Slippage tolerance in basis points (e.g., 100 = 1%)
    pub slippage_bps: u16,

    /// If true, always swap token_a to USDC on exit
    /// If false, keep both tokens
    pub force_swap_to_usdc: bool,
}

impl VaultConfig {
    pub const LEN: usize =
        2 +  // deadband_bps
        4 +  // twap_window_secs
        8 +  // cooldown_ms
        2 +  // slippage_bps
        1;   // force_swap_to_usdc

    /// Creates default configuration
    pub fn default_config() -> Self {
        Self {
            deadband_bps: 50,        // 0.5%
            twap_window_secs: 60,    // 1 minute
            cooldown_ms: 180_000,    // 3 minutes
            slippage_bps: 100,       // 1%
            force_swap_to_usdc: true,
        }
    }

    /// Validates configuration parameters
    pub fn validate(&self) -> Result<()> {
        require!(
            self.deadband_bps <= crate::constants::MAX_DEADBAND_BPS,
            crate::errors::VaultError::DeadbandExceeded
        );

        require!(
            self.slippage_bps <= crate::constants::MAX_SLIPPAGE_BPS,
            crate::errors::VaultError::SlippageExceeded
        );

        require!(
            self.cooldown_ms >= crate::constants::MIN_COOLDOWN_MS
                && self.cooldown_ms <= crate::constants::MAX_COOLDOWN_MS,
            crate::errors::VaultError::InvalidCooldown
        );

        require!(
            self.twap_window_secs >= crate::constants::MIN_TWAP_WINDOW_SECS
                && self.twap_window_secs <= crate::constants::MAX_TWAP_WINDOW_SECS,
            crate::errors::VaultError::InvalidTwapWindow
        );

        Ok(())
    }
}
