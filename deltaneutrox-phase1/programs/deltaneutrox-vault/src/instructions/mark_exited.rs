use anchor_lang::prelude::*;
use crate::state::{StrategyVault, VaultStatus};
use crate::errors::VaultError;
use crate::events::{AutoExitTriggered, StatusChanged};

#[derive(Accounts)]
pub struct MarkExited<'info> {
    #[account(mut)]
    pub vault: Account<'info, StrategyVault>,

    #[account(mut)]
    pub keeper: Signer<'info>,
}

pub fn handler(ctx: Context<MarkExited>) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    // Validate keeper
    require!(
        ctx.accounts.keeper.key() == vault.keeper_authority,
        VaultError::UnauthorizedKeeper
    );

    let old_status = vault.status_string();

    // Update status
    vault.status = VaultStatus::ExitedToUSDC;
    vault.last_exit_timestamp = clock.unix_timestamp;

    emit!(AutoExitTriggered {
        vault: vault.key(),
        reason: "manual_exit".to_string(),
        trigger_price: 0,
        liquidity_removed: 0,
        timestamp: clock.unix_timestamp,
    });

    emit!(StatusChanged {
        vault: vault.key(),
        old_status,
        new_status: vault.status_string(),
        timestamp: clock.unix_timestamp,
    });

    msg!("Vault marked as exited to USDC");

    Ok(())
}
