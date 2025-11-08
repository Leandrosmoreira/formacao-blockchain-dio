use anchor_lang::prelude::*;
use crate::state::{StrategyVault, VaultStatus};
use crate::errors::VaultError;
use crate::events::LiquidityDecreased;

#[derive(Accounts)]
pub struct DecreaseLiquidity<'info> {
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

pub fn handler(ctx: Context<DecreaseLiquidity>) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    // Validate status
    require!(
        vault.status == VaultStatus::PositionOpen,
        VaultError::NoActivePosition
    );

    // Validate keeper
    require!(
        ctx.accounts.keeper.key() == vault.keeper_authority,
        VaultError::UnauthorizedKeeper
    );

    vault.operation_in_progress = true;

    // TODO: Implement Whirlpool decrease_liquidity CPI (100%)

    vault.operation_in_progress = false;

    emit!(LiquidityDecreased {
        vault: vault.key(),
        liquidity_removed: 0, // TODO: Get actual liquidity
        amount_a: 0,
        amount_usdc: 0,
        timestamp: clock.unix_timestamp,
    });

    msg!("Liquidity decreased to 0%");

    Ok(())
}
