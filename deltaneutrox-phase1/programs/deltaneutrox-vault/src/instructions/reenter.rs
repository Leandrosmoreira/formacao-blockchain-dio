use anchor_lang::prelude::*;
use anchor_spl::token::{Token, TokenAccount};
use crate::state::{StrategyVault, VaultStatus};
use crate::errors::VaultError;
use crate::events::ReentryOpened;
use crate::cpi::whirlpool;

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

    /// CHECK: Whirlpool program
    #[account(
        constraint = whirlpool_program.key() == whirlpool::WHIRLPOOL_PROGRAM_ID @ VaultError::InvalidProgramId
    )]
    pub whirlpool_program: UncheckedAccount<'info>,

    /// CHECK: Whirlpool pool
    #[account(
        mut,
        constraint = whirlpool.key() == vault.pool_id @ VaultError::InvalidPoolId
    )]
    pub whirlpool: UncheckedAccount<'info>,

    /// CHECK: Position account (already exists)
    #[account(
        mut,
        constraint = position.key() == vault.position_key @ VaultError::PositionKeyMismatch
    )]
    pub position: UncheckedAccount<'info>,

    /// CHECK: Position token account (NFT)
    #[account(mut)]
    pub position_token_account: UncheckedAccount<'info>,

    /// Vault's token A account
    #[account(
        mut,
        constraint = vault_token_a.key() == vault.vault_token_a @ VaultError::InvalidTokenMint
    )]
    pub vault_token_a: Account<'info, TokenAccount>,

    /// Vault's USDC account
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

    /// CHECK: Tick array lower
    #[account(mut)]
    pub tick_array_lower: UncheckedAccount<'info>,

    /// CHECK: Tick array upper
    #[account(mut)]
    pub tick_array_upper: UncheckedAccount<'info>,

    /// Token program
    pub token_program: Program<'info, Token>,

    /// Keeper
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

    msg!("Re-entering position with liquidity: {}", target_liquidity);

    let elapsed_ms = ((clock.unix_timestamp - vault.last_exit_timestamp) * 1000) as u64;
    msg!("Cooldown elapsed: {} ms", elapsed_ms);

    // Get vault balances
    let balance_a = ctx.accounts.vault_token_a.amount;
    let balance_usdc = ctx.accounts.vault_usdc.amount;

    msg!("Current balances - A: {}, USDC: {}", balance_a, balance_usdc);

    // Calculate token max with slippage (add buffer)
    let slippage_multiplier = 10000u128 + vault.config.slippage_bps as u128;
    let token_max_a = ((balance_a as u128 * slippage_multiplier) / 10000) as u64;
    let token_max_b = ((balance_usdc as u128 * slippage_multiplier) / 10000) as u64;

    msg!("Token max A: {}, Token max B: {}", token_max_a, token_max_b);

    // Note: In production, the keeper should check TWAP price and potentially
    // swap some USDC -> token_a before re-entering to maintain proper ratio

    // Prepare PDA signer seeds
    let vault_key = vault.key();
    let seeds = &[
        crate::constants::VAULT_AUTHORITY_SEED,
        vault_key.as_ref(),
        &[ctx.bumps.vault_authority],
    ];
    let signer_seeds = &[&seeds[..]];

    // CPI: Increase liquidity (position already exists)
    whirlpool::increase_liquidity(
        ctx.accounts.whirlpool_program.to_account_info(),
        ctx.accounts.whirlpool.to_account_info(),
        ctx.accounts.token_program.to_account_info(),
        ctx.accounts.vault_authority.to_account_info(), // position authority
        ctx.accounts.position.to_account_info(),
        ctx.accounts.position_token_account.to_account_info(),
        ctx.accounts.vault_token_a.to_account_info(), // token owner account A
        ctx.accounts.vault_usdc.to_account_info(), // token owner account B
        ctx.accounts.token_vault_a.to_account_info(), // pool vault A
        ctx.accounts.token_vault_b.to_account_info(), // pool vault B
        ctx.accounts.tick_array_lower.to_account_info(),
        ctx.accounts.tick_array_upper.to_account_info(),
        target_liquidity,
        token_max_a,
        token_max_b,
        signer_seeds,
    )?;

    // Reload accounts to get actual amounts used
    ctx.accounts.vault_token_a.reload()?;
    ctx.accounts.vault_usdc.reload()?;

    let amount_a_used = balance_a - ctx.accounts.vault_token_a.amount;
    let amount_usdc_used = balance_usdc - ctx.accounts.vault_usdc.amount;

    // Update vault status
    vault.status = VaultStatus::PositionOpen;
    vault.operation_in_progress = false;

    emit!(ReentryOpened {
        vault: vault.key(),
        liquidity: target_liquidity,
        twap_price: 0, // TODO: Keeper should pass TWAP price
        cooldown_elapsed_ms: elapsed_ms,
        timestamp: clock.unix_timestamp,
    });

    msg!("Re-entry successful!");
    msg!("Liquidity added: {}", target_liquidity);
    msg!("Amount A used: {}", amount_a_used);
    msg!("Amount USDC used: {}", amount_usdc_used);

    Ok(())
}
