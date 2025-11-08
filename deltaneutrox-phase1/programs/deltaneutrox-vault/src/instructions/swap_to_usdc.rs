use anchor_lang::prelude::*;
use anchor_spl::token::{Token, TokenAccount, Mint};
use crate::state::StrategyVault;
use crate::errors::VaultError;
use crate::events::SwappedToUSDC;
use crate::cpi::jupiter;

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

    /// Vault's token A account (source)
    #[account(
        mut,
        constraint = vault_token_a.key() == vault.vault_token_a @ VaultError::InvalidTokenMint
    )]
    pub vault_token_a: Account<'info, TokenAccount>,

    /// Vault's USDC account (destination)
    #[account(
        mut,
        constraint = vault_usdc.key() == vault.vault_usdc @ VaultError::InvalidTokenMint
    )]
    pub vault_usdc: Account<'info, TokenAccount>,

    /// Token A mint
    #[account(
        constraint = token_a_mint.key() == vault.token_a_mint @ VaultError::InvalidTokenMint
    )]
    pub token_a_mint: Account<'info, Mint>,

    /// USDC mint
    #[account(
        constraint = usdc_mint.key() == vault.usdc_mint @ VaultError::InvalidTokenMint
    )]
    pub usdc_mint: Account<'info, Mint>,

    /// CHECK: Jupiter program
    #[account(
        constraint = jupiter_program.key() == jupiter::JUPITER_PROGRAM_ID @ VaultError::InvalidProgramId
    )]
    pub jupiter_program: UncheckedAccount<'info>,

    /// Token program
    pub token_program: Program<'info, Token>,

    /// Keeper (must be whitelisted)
    #[account(mut)]
    pub keeper: Signer<'info>,

    // Remaining accounts will be passed for Jupiter routing
    // These are determined dynamically by the Jupiter API quote
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

    // Get balance of token_a to swap
    let amount_in = ctx.accounts.vault_token_a.amount;

    if amount_in == 0 {
        msg!("No token_a balance to swap");
        return Ok(());
    }

    // Calculate minimum amount out with slippage protection
    // In production, this should come from Jupiter API quote
    // For now, we'll use a conservative estimate
    let minimum_amount_out = jupiter::calculate_min_amount_out(
        amount_in,
        vault.config.slippage_bps,
    );

    msg!("Swapping {} token_a for minimum {} USDC", amount_in, minimum_amount_out);

    // Prepare signer seeds for PDA
    let vault_key = vault.key();
    let seeds = &[
        crate::constants::VAULT_AUTHORITY_SEED,
        vault_key.as_ref(),
        &[ctx.bumps.vault_authority],
    ];
    let signer_seeds = &[&seeds[..]];

    // Get remaining accounts (passed by keeper from Jupiter API)
    let remaining_accounts = ctx.remaining_accounts;

    // Perform Jupiter swap CPI
    // Note: In production, the keeper should fetch the best route from Jupiter API
    // and pass the required accounts as remaining_accounts
    jupiter::swap_with_route(
        ctx.accounts.jupiter_program.to_account_info(),
        ctx.accounts.token_program.to_account_info(),
        ctx.accounts.vault_authority.to_account_info(),
        ctx.accounts.vault_token_a.to_account_info(),
        ctx.accounts.vault_usdc.to_account_info(),
        ctx.accounts.vault_usdc.to_account_info(), // Destination (same as vault USDC)
        ctx.accounts.token_a_mint.to_account_info(),
        ctx.accounts.usdc_mint.to_account_info(),
        ctx.accounts.vault_usdc.to_account_info(), // Platform fee account (vault gets it)
        amount_in,
        minimum_amount_out,
        0, // No platform fee
        remaining_accounts,
        signer_seeds,
    )?;

    // Reload account to get updated balance
    ctx.accounts.vault_usdc.reload()?;
    let amount_out = ctx.accounts.vault_usdc.amount;

    emit!(SwappedToUSDC {
        vault: vault.key(),
        token_a_mint: vault.token_a_mint,
        amount_in,
        amount_out,
        timestamp: clock.unix_timestamp,
    });

    msg!("Successfully swapped {} token_a to {} USDC", amount_in, amount_out);

    Ok(())
}
