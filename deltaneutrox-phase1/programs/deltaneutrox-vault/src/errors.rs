use anchor_lang::prelude::*;

#[error_code]
pub enum VaultError {
    #[msg("Invalid vault status for this operation")]
    InvalidVaultStatus,

    #[msg("Operation already in progress - reentrancy blocked")]
    OperationInProgress,

    #[msg("Unauthorized keeper - not in whitelist")]
    UnauthorizedKeeper,

    #[msg("Cooldown period not met - wait before re-entry")]
    CooldownNotMet,

    #[msg("Invalid tick range - tick_lower must be < tick_upper")]
    InvalidTickRange,

    #[msg("Slippage exceeds maximum allowed")]
    SlippageExceeded,

    #[msg("Deadband exceeds maximum allowed")]
    DeadbandExceeded,

    #[msg("Cooldown value out of allowed range")]
    InvalidCooldown,

    #[msg("TWAP window out of allowed range")]
    InvalidTwapWindow,

    #[msg("Invalid pool ID - not whitelisted")]
    InvalidPoolId,

    #[msg("Invalid token mint - does not match vault configuration")]
    InvalidTokenMint,

    #[msg("Insufficient liquidity in vault")]
    InsufficientLiquidity,

    #[msg("Insufficient shares to withdraw")]
    InsufficientShares,

    #[msg("No active position to decrease")]
    NoActivePosition,

    #[msg("Math overflow occurred")]
    MathOverflow,

    #[msg("Division by zero")]
    DivisionByZero,

    #[msg("Invalid program ID for CPI")]
    InvalidProgramId,

    #[msg("Position key mismatch")]
    PositionKeyMismatch,

    #[msg("Vault not properly exited - complete exit flow first")]
    NotProperlyExited,

    #[msg("Cannot withdraw while operation in progress")]
    CannotWithdrawDuringOperation,
}
