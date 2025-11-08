use anchor_lang::prelude::*;
use crate::state::StrategyVault;
use crate::errors::VaultError;
use crate::events::FeesCollected;

#[derive(Accounts)]
pub struct CollectFees<'info> {
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

pub fn handler(ctx: Context<CollectFees>) -> Result<()> {
    let vault = &ctx.accounts.vault;
    let clock = Clock::get()?;

    // Validate keeper
    require!(
        ctx.accounts.keeper.key() == vault.keeper_authority,
        VaultError::UnauthorizedKeeper
    );

    // TODO: Implement Whirlpool collect_fees CPI

    emit!(FeesCollected {
        vault: vault.key(),
        amount_a: 0,
        amount_usdc: 0,
        timestamp: clock.unix_timestamp,
    });

    msg!("Fees collected");

    Ok(())
}
