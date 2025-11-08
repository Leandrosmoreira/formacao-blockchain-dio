use anchor_lang::prelude::*;
use crate::state::{StrategyVault, VaultStatus};
use crate::errors::VaultError;
use crate::events::ReentryOpened;

#[derive(Accounts)]
pub struct Reenter<'info> {
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
    ctx: Context<Reenter>,
    target_liquidity: u128,
) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    // Validate status
    require!(
        vault.status == VaultStatus::ExitedToUSDC,
        VaultError::InvalidVaultStatus
    );

    // Validate keeper
    require!(
        ctx.accounts.keeper.key() == vault.keeper_authority,
        VaultError::UnauthorizedKeeper
    );

    // Check cooldown
    require!(
        vault.can_reenter(clock.unix_timestamp),
        VaultError::CooldownNotMet
    );

    vault.operation_in_progress = true;

    // TODO: Implement re-entry logic
    // 1. Calculate amounts needed for target_liquidity
    // 2. Jupiter CPI: swap USDC -> token_a (if needed)
    // 3. Whirlpool CPI: increase_liquidity

    vault.status = VaultStatus::PositionOpen;
    vault.operation_in_progress = false;

    let elapsed_ms = ((clock.unix_timestamp - vault.last_exit_timestamp) * 1000) as u64;

    emit!(ReentryOpened {
        vault: vault.key(),
        liquidity: target_liquidity,
        twap_price: 0, // TODO: Get from Pyth
        cooldown_elapsed_ms: elapsed_ms,
        timestamp: clock.unix_timestamp,
    });

    msg!("Re-entered position with liquidity: {}", target_liquidity);

    Ok(())
}
