use anchor_lang::prelude::*;
use crate::state::{StrategyVault, VaultStatus};
use crate::errors::VaultError;
use crate::events::PositionOpened;

#[derive(Accounts)]
pub struct OpenPosition<'info> {
    #[account(mut)]
    pub vault: Account<'info, StrategyVault>,

    /// CHECK: Vault authority PDA
    #[account(
        seeds = [crate::constants::VAULT_AUTHORITY_SEED, vault.key().as_ref()],
        bump
    )]
    pub vault_authority: UncheckedAccount<'info>,

    #[account(mut)]
    pub keeper: Signer<'info>,
}

pub fn handler(
    ctx: Context<OpenPosition>,
    liquidity: u128,
) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    // Validate status
    require!(
        vault.status == VaultStatus::Idle || vault.status == VaultStatus::ExitedToUSDC,
        VaultError::InvalidVaultStatus
    );

    // Validate keeper
    require!(
        ctx.accounts.keeper.key() == vault.keeper_authority,
        VaultError::UnauthorizedKeeper
    );

    // Set reentrancy lock
    vault.operation_in_progress = true;

    // TODO: Implement Whirlpool CPI
    // 1. open_position_with_metadata
    // 2. increase_liquidity

    // For now, just update status
    vault.status = VaultStatus::PositionOpen;
    vault.operation_in_progress = false;

    emit!(PositionOpened {
        vault: vault.key(),
        position_key: vault.position_key,
        liquidity,
        amount_a: 0, // TODO: Get from Whirlpool
        amount_usdc: 0,
        tick_lower: vault.tick_lower,
        tick_upper: vault.tick_upper,
        timestamp: clock.unix_timestamp,
    });

    msg!("Position opened with liquidity: {}", liquidity);

    Ok(())
}
