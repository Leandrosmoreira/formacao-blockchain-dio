use anchor_lang::prelude::*;
use super::VaultConfig;

#[account]
#[derive(Default)]
pub struct StrategyVault {
    /// Authority PDA that can sign for the vault
    pub authority: Pubkey,

    /// Whirlpool pool address
    pub pool_id: Pubkey,

    /// Whirlpool position NFT mint
    pub position_key: Pubkey,

    /// Token A mint (volatile token, e.g., SOL)
    pub token_a_mint: Pubkey,

    /// USDC mint
    pub usdc_mint: Pubkey,

    /// Shares mint (LP token for vault depositors)
    pub shares_mint: Pubkey,

    /// Vault's token A account (ATA)
    pub vault_token_a: Pubkey,

    /// Vault's USDC account (ATA)
    pub vault_usdc: Pubkey,

    /// Lower tick of the price range
    pub tick_lower: i32,

    /// Upper tick of the price range
    pub tick_upper: i32,

    /// Current vault status
    pub status: VaultStatus,

    /// Reentrancy lock
    pub operation_in_progress: bool,

    /// Strategy configuration parameters
    pub config: VaultConfig,

    /// Total shares minted
    pub total_shares: u64,

    /// Last exit timestamp (for cooldown enforcement)
    pub last_exit_timestamp: i64,

    /// Total deposits tracking
    pub total_deposits: u64,

    /// Total withdrawals tracking
    pub total_withdrawals: u64,

    /// Keeper authority (whitelisted for auto-exit/reentry)
    pub keeper_authority: Pubkey,

    /// Bump seed for PDA
    pub bump: u8,
}

impl StrategyVault {
    /// Space required for the account
    /// Discriminator (8) + all fields
    pub const LEN: usize = 8 + // discriminator
        32 + // authority
        32 + // pool_id
        32 + // position_key
        32 + // token_a_mint
        32 + // usdc_mint
        32 + // shares_mint
        32 + // vault_token_a
        32 + // vault_usdc
        4 +  // tick_lower
        4 +  // tick_upper
        1 +  // status (enum)
        1 +  // operation_in_progress
        VaultConfig::LEN + // config
        8 +  // total_shares
        8 +  // last_exit_timestamp
        8 +  // total_deposits
        8 +  // total_withdrawals
        32 + // keeper_authority
        1 +  // bump
        64;  // padding for future upgrades

    /// Returns the status as a string for events
    pub fn status_string(&self) -> String {
        match self.status {
            VaultStatus::Idle => "Idle".to_string(),
            VaultStatus::PositionOpen => "PositionOpen".to_string(),
            VaultStatus::ExitedToUSDC => "ExitedToUSDC".to_string(),
            VaultStatus::Reentering => "Reentering".to_string(),
        }
    }

    /// Check if vault is ready for re-entry (cooldown passed)
    pub fn can_reenter(&self, current_timestamp: i64) -> bool {
        if self.status != VaultStatus::ExitedToUSDC {
            return false;
        }

        let elapsed_ms = ((current_timestamp - self.last_exit_timestamp) * 1000) as u64;
        elapsed_ms >= self.config.cooldown_ms
    }
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, Default)]
pub enum VaultStatus {
    #[default]
    /// Vault created, no position open
    Idle,

    /// LP position is active in Whirlpool
    PositionOpen,

    /// Exited from position and all converted to USDC
    ExitedToUSDC,

    /// Currently in re-entry process
    Reentering,
}
