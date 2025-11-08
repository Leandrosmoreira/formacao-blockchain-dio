use anchor_lang::prelude::*;
use anchor_spl::token::{Token, TokenAccount};
use crate::state::StrategyVault;
use crate::errors::VaultError;
use crate::events::FeesCollected;
use crate::cpi::whirlpool;

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

    /// CHECK: Whirlpool program
    #[account(
        constraint = whirlpool_program.key() == whirlpool::WHIRLPOOL_PROGRAM_ID @ VaultError::InvalidProgramId
    )]
    pub whirlpool_program: UncheckedAccount<'info>,

    /// CHECK: Whirlpool pool
    #[account(
        constraint = whirlpool.key() == vault.pool_id @ VaultError::InvalidPoolId
    )]
    pub whirlpool: UncheckedAccount<'info>,

    /// CHECK: Position account
    #[account(
        mut,
        constraint = position.key() == vault.position_key @ VaultError::PositionKeyMismatch
    )]
    pub position: UncheckedAccount<'info>,

    /// CHECK: Position token account (NFT)
    #[account(mut)]
    pub position_token_account: UncheckedAccount<'info>,

    /// Vault's token A account (receives fees)
    #[account(
        mut,
        constraint = vault_token_a.key() == vault.vault_token_a @ VaultError::InvalidTokenMint
    )]
    pub vault_token_a: Account<'info, TokenAccount>,

    /// Vault's USDC account (receives fees)
    #[account(
        mut,
        constraint = vault_usdc.key() == vault.vault_usdc @ VaultError::InvalidTokenMint
    )]
    pub vault_usdc: Account<'info, TokenAccount>,

    /// CHECK: Pool's token A vault
    #[account(mut)]
    pub token_vault_a: UncheckedAccount<'info>,

    /// CHECK: Pool's token B (USDC) vault
    #[account(mut)]
    pub token_vault_b: UncheckedAccount<'info>,

    /// Token program
    pub token_program: Program<'info, Token>,

    /// Keeper
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

    msg!("Collecting fees from position: {}", vault.position_key);

    // Get balances before collecting fees
    let balance_a_before = ctx.accounts.vault_token_a.amount;
    let balance_usdc_before = ctx.accounts.vault_usdc.amount;

    // Prepare PDA signer seeds
    let vault_key = vault.key();
    let seeds = &[
        crate::constants::VAULT_AUTHORITY_SEED,
        vault_key.as_ref(),
        &[ctx.bumps.vault_authority],
    ];
    let signer_seeds = &[&seeds[..]];

    // CPI: Collect fees
    whirlpool::collect_fees(
        ctx.accounts.whirlpool_program.to_account_info(),
        ctx.accounts.whirlpool.to_account_info(),
        ctx.accounts.vault_authority.to_account_info(), // position authority
        ctx.accounts.position.to_account_info(),
        ctx.accounts.position_token_account.to_account_info(),
        ctx.accounts.vault_token_a.to_account_info(), // token owner account A
        ctx.accounts.vault_usdc.to_account_info(), // token owner account B
        ctx.accounts.token_vault_a.to_account_info(), // pool vault A
        ctx.accounts.token_vault_b.to_account_info(), // pool vault B
        ctx.accounts.token_program.to_account_info(),
        signer_seeds,
    )?;

    // Reload accounts to get fees collected
    ctx.accounts.vault_token_a.reload()?;
    ctx.accounts.vault_usdc.reload()?;

    let fees_a = ctx.accounts.vault_token_a.amount - balance_a_before;
    let fees_usdc = ctx.accounts.vault_usdc.amount - balance_usdc_before;

    emit!(FeesCollected {
        vault: vault.key(),
        amount_a: fees_a,
        amount_usdc: fees_usdc,
        timestamp: clock.unix_timestamp,
    });

    msg!("Fees collected successfully!");
    msg!("Fee A: {}", fees_a);
    msg!("Fee USDC: {}", fees_usdc);

    Ok(())
}
