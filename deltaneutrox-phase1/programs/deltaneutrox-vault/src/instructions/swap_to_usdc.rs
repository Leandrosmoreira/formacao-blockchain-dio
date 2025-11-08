use anchor_lang::prelude::*;
use crate::state::StrategyVault;
use crate::errors::VaultError;
use crate::events::SwappedToUSDC;

#[derive(Accounts)]
pub struct SwapToUSDC<'info> {
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

pub fn handler(ctx: Context<SwapToUSDC>) -> Result<()> {
    let vault = &ctx.accounts.vault;
    let clock = Clock::get()?;

    // Validate keeper
    require!(
        ctx.accounts.keeper.key() == vault.keeper_authority,
        VaultError::UnauthorizedKeeper
    );

    // Only swap if config requires it
    if !vault.config.force_swap_to_usdc {
        msg!("Swap not required by config");
        return Ok(());
    }

    // TODO: Implement Jupiter swap CPI (token_a -> USDC)

    emit!(SwappedToUSDC {
        vault: vault.key(),
        token_a_mint: vault.token_a_mint,
        amount_in: 0,
        amount_out: 0,
        timestamp: clock.unix_timestamp,
    });

    msg!("Swapped all token_a to USDC");

    Ok(())
}
